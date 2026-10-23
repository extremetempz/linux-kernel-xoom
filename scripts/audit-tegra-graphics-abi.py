#!/usr/bin/env python3
"""Measure pinned Tegra graphics C layouts with ARM GCC; never execute them.

Uses existing local repositories and the project's existing cross-compiler.
No fetching, kernel builds, device access or tracked-file writes are performed.
A completed measurement is NOT a graphics compatibility verdict.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE = 256 * 1024
MAX_OBJECT = 1024 * 1024
MAX_JSON = 64 * 1024
PINS = {
    "baseline": "6b3d70fff905b7395fd15992c3779b27d1b6c101",
    "elementalx": "3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd",
    "donor_base": "bbcece6d21c83b6280061a91d27566aff1951c94",
}
ORIGINAL_HEADERS = {
    "nvmap": "drivers/video/tegra/nvmap/nvmap_ioctl.h",
    "nvhost": "arch/arm/mach-tegra/include/mach/nvhost.h",
}
DONOR_HEADERS = {
    "nvmap": "drivers/staging/tegra/video/nvmap/nvmap_ioctl.h",
    "nvhost": "drivers/staging/tegra/include/linux/nvhost_ioctl.h",
}
FLAGS = [
    "-std=gnu11", "-nostdinc", "-marm", "-march=armv7-a",
    "-mfloat-abi=softfp", "-mfpu=vfpv3-d16", "-fno-pic",
    "-fno-stack-protector", "-Wall", "-Wextra", "-Werror", "-O0",
]
TYPE_EXPRESSIONS = {
    "unsigned int": "sizeof(unsigned int)",
    "unsigned long": "sizeof(unsigned long)",
    "pointer": "sizeof(void *)",
    "__u32": "sizeof(__u32)",
    "__s32": "sizeof(__s32)",
    "__u64": "sizeof(__u64)",
}
TYPE_PREFIX = """/* Fixed-width aliases used by the inspected ARM headers. */
typedef unsigned int __u32;
typedef signed int __s32;
typedef unsigned long long __u64;
#define __user
_Static_assert(__CHAR_BIT__ == 8, "8-bit bytes required");
_Static_assert(sizeof(unsigned int) == 4, "ARM32 int required");
_Static_assert(sizeof(unsigned long) == 4, "ARM32 long required");
_Static_assert(sizeof(void *) == 4, "ARM32 pointer required");
_Static_assert(sizeof(__u64) == 8, "64-bit __u64 required");
"""


class AuditError(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(args, limit=MAX_SOURCE, timeout=30):
    try:
        result = subprocess.run(
            [str(arg) for arg in args], capture_output=True, timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuditError(f"Cannot run {args[0]}: {error}") from error
    if len(result.stdout) > limit or len(result.stderr) > limit:
        raise AuditError(f"Output exceeded the {limit}-byte bound: {args[0]}")
    if result.returncode:
        detail = result.stderr.decode(errors="replace")[:2000].strip()
        raise AuditError(f"Command failed ({result.returncode}): {args[0]}: {detail}")
    return result.stdout


def git(repo, *args):
    return run(["git", "-C", repo, *args])


def resolve(repo, revision):
    try:
        value = git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    except AuditError as error:
        raise AuditError(
            f"Missing local repository or commit {revision} in {repo}. "
            "Use the project's existing source setup first; this audit never fetches."
        ) from error
    value = value.decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise AuditError(f"Unexpected commit identifier in {repo}")
    return value


def source(repo, revision, path):
    data = git(repo, "show", f"{revision}:{path}")
    try:
        return data.decode("utf-8"), {"path": path, "sha256": sha(data)}
    except UnicodeDecodeError as error:
        raise AuditError(f"Non-text source header: {path}") from error


def extract(header, family, original):
    """Keep the actual ABI declarations, excluding kernel-private includes/APIs."""
    try:
        if family == "nvmap":
            text = header[header.index("enum {"):header.index("#define NVMAP_IOC_MAXNR")]
        else:
            marker = "#define NVHOST_NO_TIMEOUT" if original else "#define NVHOST_INVALID_SYNCPOINT"
            text = header[header.index(marker):header.rindex("#endif")]
    except ValueError as error:
        raise AuditError(f"Unrecognized {family} header layout; review extraction") from error
    if re.search(r"^\s*#\s*include\b", text, re.M):
        raise AuditError("Unexpected include in extracted ABI declarations")
    logical = re.sub(r"\\\r?\n", "", text)
    names = re.findall(
        r"^#define ((?:NVMAP_IOC|NVHOST_IOCTL)_[A-Z0-9_]+)\s+_IO(?:WR|W|R)?\(",
        logical, re.M,
    )
    structures = re.findall(r"^struct ((?:nvmap|nvhost)_[a-z0-9_]+)\s*\{", text, re.M)
    if not names or not structures or len(names) > 64 or len(structures) > 32:
        raise AuditError("Missing or unexpectedly large ABI declaration set")
    if len(set(names)) != len(names) or len(set(structures)) != len(structures):
        raise AuditError("Duplicate extracted ABI names")
    return text, names, structures


def elf_values(path, count):
    """Read a constant section from an ARM32 relocatable object, without running it."""
    size = path.stat().st_size
    if not 52 <= size <= MAX_OBJECT:
        raise AuditError("Compiled object has an unexpected size")
    data = path.read_bytes()
    if data[:7] != b"\x7fELF\x01\x01\x01":
        raise AuditError("Compiler did not produce little-endian ELF32")
    fields = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    if fields[1:3] != (1, 40):
        raise AuditError("Expected an ARM relocatable object, not an executable")
    shoff, shentsize, shnum, shstrndx = fields[6], fields[11], fields[12], fields[13]
    if shentsize != 40 or not 1 <= shnum <= 64 or shstrndx >= shnum:
        raise AuditError("Unexpected ELF section table")
    if shoff + shentsize * shnum > len(data):
        raise AuditError("ELF section table is out of bounds")
    sections = [struct.unpack_from("<10I", data, shoff + i * shentsize) for i in range(shnum)]

    def contents(section):
        offset, length = section[4:6]
        if offset + length > len(data):
            raise AuditError("ELF section data is out of bounds")
        return data[offset:offset + length]

    strings = contents(sections[shstrndx])
    found = []
    for section in sections:
        offset = section[0]
        if offset >= len(strings):
            raise AuditError("ELF section name is out of bounds")
        end = strings.find(b"\0", offset)
        if end < 0:
            raise AuditError("Unterminated ELF section name")
        if strings[offset:end] == b".xoom_abi":
            found.append(section)
    if len(found) != 1 or found[0][1] != 1:
        raise AuditError("Expected one constant .xoom_abi section")
    raw = contents(found[0])
    if len(raw) != count * 4:
        raise AuditError("Compiled ABI value count does not match declarations")
    return struct.unpack("<" + "I" * count, raw)


def measure(cc, directory, name, family, header, ioctl_header, original):
    body, names, structures = extract(header, family, original)
    expressions = list(TYPE_EXPRESSIONS.values()) + names + [
        f"sizeof(struct {item})" for item in structures
    ]
    text = TYPE_PREFIX + ioctl_header + "\n" + body + "\n"
    text += '__attribute__((used, section(".xoom_abi"))) const unsigned int xoom_abi_values[] = {\n'
    text += ",\n".join(expressions) + "\n};\n"
    c_path = directory / f"{name}-{family}.c"
    object_path = c_path.with_suffix(".o")
    c_path.write_text(text)
    run([cc, *FLAGS, "-c", c_path, "-o", object_path], timeout=60)
    values = iter(elf_values(object_path, len(expressions)))
    types = {item: next(values) for item in TYPE_EXPRESSIONS}
    ioctls = {item: f"0x{next(values):08x}" for item in names}
    sizes = {item: next(values) for item in structures}
    return {
        "target_type_sizes_bytes": types,
        "ioctl_encodings": ioctls,
        "struct_sizes_bytes": sizes,
        "generated_c_sha256": sha(c_path.read_bytes()),
        "compiled_arm_object_sha256": sha(object_path.read_bytes()),
    }


def compare(measurements):
    nvmap = [item["nvmap"] for item in measurements.values()]
    nvhost = [item["nvhost"] for item in measurements.values()]
    common = set.intersection(*(set(item["ioctl_encodings"]) for item in nvhost))
    submits = {
        name: item["nvhost"]["struct_sizes_bytes"]["nvhost_submit_hdr"]
        for name, item in measurements.items()
    }
    return {
        "compatibility_verdict": "not_established",
        "shared_nvmap_ioctl_count": len(nvmap[0]["ioctl_encodings"]),
        "all_nvmap_ioctl_encodings_equal": all(
            item["ioctl_encodings"] == nvmap[0]["ioctl_encodings"] for item in nvmap
        ),
        "all_nvmap_struct_sizes_equal": all(
            item["struct_sizes_bytes"] == nvmap[0]["struct_sizes_bytes"] for item in nvmap
        ),
        "shared_nvhost_ioctl_count": len(common),
        "shared_nvhost_ioctl_encodings_equal": all(
            len({item["ioctl_encodings"][key] for item in nvhost}) == 1 for key in common
        ),
        "nvhost_write_submit_header_sizes_bytes": submits,
        "nvhost_write_submit_layouts_differ": len(set(submits.values())) != 1,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT / "sources/kernel-baseline")
    parser.add_argument("--elementalx", type=Path, default=ROOT / "sources/kernel-elementalx-review")
    parser.add_argument("--donor", type=Path, default=ROOT / "sources/kernel-donor")
    parser.add_argument("--compiler", type=Path,
                        default=ROOT / "toolchains/android-gcc49/bin/arm-linux-androideabi-gcc")
    parser.add_argument("--save-dir", type=Path,
                        help="Preserve evidence in a new directory; existing paths are refused")
    args = parser.parse_args()
    if not args.compiler.is_file():
        raise AuditError("Cross-compiler is missing; run scripts/setup-toolchain.sh first. No fetching was attempted.")
    cc = args.compiler.absolute()
    version = run([cc, "--version"], limit=8192).decode().strip()
    machine = run([cc, "-dumpmachine"], limit=1024).decode().strip()
    if "4.9" not in version or machine != "arm-linux-androideabi":
        raise AuditError("This measurement requires the project's ARM Android GCC 4.9 toolchain")
    if args.save_dir is not None and args.save_dir.exists():
        raise AuditError(f"Refusing to overwrite existing evidence directory: {args.save_dir}")

    heads = {name: resolve(repo, "HEAD") for name, repo in (
        ("baseline", args.baseline), ("elementalx", args.elementalx), ("donor", args.donor)
    )}
    specs = [
        ("baseline", args.baseline, PINS["baseline"], True),
        ("elementalx", args.elementalx, PINS["elementalx"], True),
        ("donor_base", args.donor, PINS["donor_base"], False),
        ("wingray_current", args.donor, heads["donor"], False),
    ]
    resolve(args.donor, PINS["donor_base"])
    git(args.donor, "merge-base", "--is-ancestor", PINS["donor_base"], heads["donor"])
    sources, measurements = {}, {}
    with tempfile.TemporaryDirectory(prefix="xoom-graphics-abi-") as temporary:
        directory = Path(temporary)
        for name, repo, revision, original in specs:
            revision = resolve(repo, revision)
            ioctl_path = "include/asm-generic/ioctl.h" if original else "include/uapi/asm-generic/ioctl.h"
            ioctl, ioctl_meta = source(repo, revision, ioctl_path)
            if re.search(r"^\s*#\s*include\b", ioctl, re.M):
                raise AuditError("Unexpected include in generic ioctl encoding header")
            arm_path = "arch/arm/include/asm/ioctl.h" if original else "arch/arm/include/asm/Kbuild"
            arm, arm_meta = source(repo, revision, arm_path)
            if original:
                arm_generic = arm.strip() == "#include <asm-generic/ioctl.h>"
            else:
                arm_generic = bool(re.search(r"^generic-y\s*\+=\s*ioctl\.h\s*$", arm, re.M))
            if not arm_generic:
                raise AuditError("ARM ioctl encoding no longer selects the inspected generic header")
            sources[name] = {
                "compared_commit": revision,
                "checkout_head": heads["donor" if name in ("donor_base", "wingray_current") else name],
                "committed_files_only": True,
                "ioctl_encoding_header": ioctl_meta,
                "arm_ioctl_selection": arm_meta,
                "headers": {},
            }
            measurements[name] = {}
            for family, path in (ORIGINAL_HEADERS if original else DONOR_HEADERS).items():
                header, metadata = source(repo, revision, path)
                sources[name]["headers"][family] = metadata
                measurements[name][family] = measure(
                    cc, directory, name, family, header, ioctl, original,
                )
        report = {
            "schema_version": 1,
            "measurement_only": True,
            "compiler": {"version": version, "target": machine, "flags": FLAGS,
                         "launcher_sha256": sha(cc.read_bytes())},
            "sources": sources,
            "measurements": measurements,
            "comparison": compare(measurements),
            "limits": [
                "No compiled code was executed; only ARM32 relocatable-object constants were read.",
                "Committed header declarations were extracted; uncommitted edits are not measured.",
                "Equal ioctl numbers and sizes do not prove semantics, member offsets, cache coherency or blob compatibility.",
                "Installed baseline binary/source identity and proprietary-library submission dialect remain unproven.",
                "No device access, flashing, network fetch, driver activation or board configuration change occurred.",
            ],
        }
        output = json.dumps(report, indent=2) + "\n"
        if len(output.encode()) > MAX_JSON:
            raise AuditError("JSON report exceeded its 64 KiB bound")
        (directory / "comparison.json").write_text(output)
        if args.save_dir is not None:
            args.save_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(directory, args.save_dir)
        sys.stdout.write(output)


if __name__ == "__main__":
    try:
        main()
    except AuditError as error:
        print(f"Tegra graphics ABI measurement failed: {error}", file=sys.stderr)
        sys.exit(1)
