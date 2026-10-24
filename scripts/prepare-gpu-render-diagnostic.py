#!/usr/bin/env python3
"""Pack a bounded offscreen GPU test entirely in RAM; no device operations."""
from pathlib import Path
import argparse, gzip, hashlib, json, re, stat, struct, subprocess
from android44_image import (Entry, original_entries, default_properties,
                             pack_newc, parse_newc, boot_image, BUSYBOX_SHA256)
from gpu_test import validate_artifacts

ROOT = Path(__file__).resolve().parents[1]
TRACE_SHA = 'cdd7ab77abfe739b6425eaa1eb7644ec8f019579fbc65ef90734b49854968875'
PROBE_SHA = '606d7757d6b290599bb3e6c0f7de8f88d35c91d66ac17df591b29582e37abb1d'
RECOVERY_SHA = '5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def runtime_files():
    private = ROOT/'artifacts/hardware-private'
    trace = (ROOT/'artifacts/original-egl-submission46-raw/submission-trace-private.txt').read_bytes()
    assert sha(trace) == TRACE_SHA
    files = {
        'bin/busybox': ROOT/'artifacts/busybox-static-armv5l',
        'system/bin/linker': private/'linker',
        'system/bin/sh': ROOT/'artifacts/gpu-runtime48-inputs/android-sh',
        'system/lib/xoom-egl-probe.so': ROOT/'artifacts/kitkat-egl-probe41-v2/xoom-egl-probe.so',
    }
    assert sha(files['bin/busybox'].read_bytes()) == BUSYBOX_SHA256
    assert sha(files['system/lib/xoom-egl-probe.so'].read_bytes()) == PROBE_SHA
    # Only successfully opened original-ROM libraries; no decoded command replay.
    for line in trace.decode().splitlines():
        m = re.search(r'open\("((?:\\x[0-9a-f]{2})+)".*\)\s+= \d+$', line)
        if not m:
            continue
        name = bytes.fromhex(m[1].replace('\\x', '')).decode()
        if name.startswith('/system/lib/') and name.endswith('.so'):
            files[name[1:]] = private/'system-lib'/name.removeprefix('/system/lib/')
    assert len([n for n in files if n.startswith('system/lib/')]) == 28
    pending = list(files.values())
    while pending:
        path = pending.pop()
        data = path.read_bytes()
        assert data[:7] == b'\x7fELF\x01\x01\x01' and struct.unpack_from('<H', data, 18)[0] == 40, path
        dynamic = subprocess.check_output(['readelf', '-dW', str(path)], text=True)
        for lib in re.findall(r'Shared library: \[([^\]]+)\]', dynamic):
            assert '/' not in lib and lib.endswith('.so')
            name = 'system/lib/'+lib
            if name not in files:
                files[name] = private/'system-lib'/lib
                pending.append(files[name])
    assert not any('GLES_android' in n or 'swiftshader' in n.lower() for n in files)
    return files

def entries(files):
    original = original_entries((ROOT/'artifacts/hardware-private/backup-boot.img').read_bytes())
    e = {}
    for name in ('.', 'ueventd.rc', 'ueventd.stingray.rc', 'file_contexts',
                 'property_contexts', 'sepolicy', 'seapp_contexts'):
        e[name] = original[name]
    item = original['init']
    e['init.android'] = Entry('init.android', item.mode, item.data)
    for name in ('bin', 'sbin', 'system', 'system/bin', 'system/lib', 'system/lib/egl',
                 'system/lib/hw', 'dev', 'proc', 'sys', 'run', 'tmp', 'data', 'cache'):
        e[name] = Entry(name, stat.S_IFDIR | 0o755)
    for name, target in {'bin/sh': 'busybox', 'sbin/ueventd': '/init.android',
                         'vendor': '/system/vendor'}.items():
        e[name] = Entry(name, stat.S_IFLNK | 0o777, target.encode())
    for name, path in files.items():
        e[name] = Entry(name, stat.S_IFREG | 0o755, path.read_bytes())
    scripts = {'init': 'gpu-render-init.sh', 'bin/gpu-render-start': 'gpu-render-start.sh',
               'bin/gpu-render-report': 'gpu-render-report.sh',
               'bin/diagnostic-server': 'server.sh', 'bin/usb-report-loop': 'usb-report-loop.sh'}
    for name, path in scripts.items():
        e[name] = Entry(name, stat.S_IFREG | 0o755, (ROOT/'diagnostic'/path).read_bytes())
    report = (ROOT/'diagnostic/report.sh').read_bytes()
    anchor = b"/bin/busybox printf 'XOOM_DMESG_BEGIN"
    assert report.count(anchor) == 1
    e['bin/diagnostic-report'] = Entry('bin/diagnostic-report', stat.S_IFREG | 0o755,
        report.replace(anchor, b'/bin/busybox sh /bin/gpu-render-report\n'+anchor))
    e['init.rc'] = Entry('init.rc', stat.S_IFREG | 0o644, (ROOT/'diagnostic/gpu-render.rc').read_bytes())
    e['default.prop'] = Entry('default.prop', stat.S_IFREG | 0o644,
        default_properties(original['default.prop'].data)+b'ro.board.platform=tegra\nro.product.device=wingray\n')
    e['system/build.prop'] = Entry('system/build.prop', stat.S_IFREG | 0o644,
        (ROOT/'artifacts/lockscreen-reference-28/additional-runtime/build.prop').read_bytes())
    for name, major, minor in [('console', 5, 1), ('null', 1, 3)]:
        e['dev/'+name] = Entry('dev/'+name, stat.S_IFCHR | 0o600, major=major, minor=minor)
    assert parse_newc(pack_newc(e)) == e
    assert not any(n.startswith('fstab') or n.startswith('init.') and n not in {'init.android', 'init.rc'} for n in e)
    assert 'import ' not in e['init.rc'].data.decode()
    assert not any(x in e['init.rc'].data for x in (b'mount ', b'class_start', b'zygote', b'surfaceflinger'))
    return e

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel-dir', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args(); out = a.output_dir.resolve()
    assert out.is_relative_to(ROOT/'artifacts') and not out.exists()
    validate_artifacts(a.kernel_dir)
    recovery = ROOT/'artifacts/hardware-private/backup-recovery.img'
    assert sha(recovery.read_bytes()) == RECOVERY_SHA
    files = runtime_files(); archive = pack_newc(entries(files))
    assert len(archive) < 16*1024*1024
    ramdisk = gzip.compress(archive, mtime=0)
    kernel = (a.kernel_dir/'zImage-dtb').read_bytes()
    image = boot_image(kernel, ramdisk)
    assert len(image) < 8*1024*1024
    manifest = {'purpose': 'fixed-clock NVIDIA offscreen two-frame readback, not Android composition',
        'hardware_executed': False, 'acceleration_proven': False,
        'sha256': sha(image), 'size': len(image), 'kernel_sha256': sha(kernel),
        'ramdisk_sha256': sha(ramdisk), 'ramdisk_uncompressed_size': len(archive),
        'runtime_sha256': {n: sha(p.read_bytes()) for n, p in sorted(files.items())},
        'storage_mounts': [], 'services': ['ueventd', 'gpu-probe'],
        'probe_timeout_seconds': 35, 'trace_sha256': TRACE_SHA,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
            [Path(__file__).resolve(), ROOT/'scripts/gpu_test.py', ROOT/'scripts/android44_image.py',
             *[ROOT/'diagnostic'/n for n in ['gpu-render-init.sh', 'gpu-render-start.sh',
                'gpu-render-report.sh', 'gpu-render.rc', 'server.sh', 'usb-report-loop.sh', 'report.sh']]]}}
    out.mkdir()
    (out/'ramdisk.cpio.gz').write_bytes(ramdisk)
    (out/'wingray-gpu-render-diagnostic.img').write_bytes(image)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    assert sha(recovery.read_bytes()) == RECOVERY_SHA
    print('Prepared RAM-only GPU test; not flashed:', out, 'bytes:', len(image))

if __name__ == '__main__':
    main()
