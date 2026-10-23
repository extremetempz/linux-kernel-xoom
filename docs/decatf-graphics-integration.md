# Decatf legacy graphics integration — 24 October 2026

This records the earlier full-link checkpoint. Subsequent
[resource and framebuffer code changes](graphics-compatibility-42.md) add
reservation checks and an initial optional RGB compatibility path; they still
do not establish accelerated graphics on hardware.

The existing Decatf nvhost/host1x, GR2D/GR3D, nvmap, display-controller and
framebuffer drivers now pass a complete ARM `vmlinux` link without selecting
Samsung's CMC623 panel driver. **This is an offline build result, not working
accelerated graphics.** No graphics boot image was packaged or flashed.

The tested display/touch/software-graphics and two-core configurations remain
unchanged. Original boot and recovery remain preserved; no restoration is
pending. No Samsung regulator tables, pinmux, panel timings or power sequencing
were imported. Scaling and voltage management remain disabled.

## Reused implementation and separate corrections

Reuse the existing `drivers/staging/tegra/video/` implementation from
[Decatf's pinned donor](https://github.com/Decatf/linux/tree/bbcece6d21c83b6280061a91d27566aff1951c94).
The following small corrections make its non-Samsung build consistent; they
do not replace its engine, allocator, rendering or synchronization code.

| Patch | Source commit | Correction |
|---|---|---|
| 0071 | `c69418dd` | Compile CMC623 includes, clock votes and suspend/resume hooks only when that panel driver is selected. Generic backlight regulator behavior remains. |
| 0072 | `5e83e15b` | Make the controller-enable function's two-argument signature agree with its caller. Preserve the existing Samsung reset-skip behavior; generic boards still reset. |
| 0073 | `8467dab8` | Restrict the default CMC623 selection to the Samsung board configuration. Previously it selected itself for Wingray and failed its panel-tuning build. |
| 0074 | `a41e846e` | Correct `!CONFIG_TEGRA20_MC` to `!TEGRA20_MC` in Kconfig, so the real modern memory-controller driver excludes the legacy downstream stack. |

The source delta from the preceding `b6483deb` checkpoint touches only three
staging files: 11 insertions and 13 deletions. No defconfig or device tree is
changed. Legacy graphics and modern DRM/host1x remain alternative owners.

## Verified offline checks

- Full ARM link at source `a41e846e` includes `nvhost_probe`, `nvmap_probe`,
  `tegra_dc_probe` and `tegra_fb_register`, and excludes CMC623 hooks and the
  modern Tegra DRM probe. Private artifacts are retained under
  `artifacts/decatf-graphics-full-link-39/` with hashes and the resolved config.
  This directory number is a compile checkpoint, **not a physical boot attempt**.
- The actual Kconfig resolver, with the parent MEMORY menu enabled, accepts
  modern `TEGRA20_MC=y` and excludes `TEGRA_DOWNSTREAM`. The earlier test that
  omitted the parent menu was inconclusive and was replaced by this test.
- The actual clock/backlight functions pass CMC-on and CMC-off provider tests.
  The old non-CMC source fails the negative compile control. These tests do not
  measure physical regulators, clocks or panel behavior.
- ARM32 compiled declarations from the original Motorola/ElementalX headers
  agree on framebuffer request numbers, sizes and member offsets. The current
  donor still lacks the two requests identified below. Generated ARM objects
  are inspected, never executed.

Reproduce using the existing pinned local sources/toolchain:

```sh
python3 tests/test-tegra-dc-panel-guards.py
python3 scripts/audit-tegra-fb-abi.py --save-dir artifacts/new-fb-abi-review
XOOM_GRAPHICS_ARTIFACT_DIR="$PWD/artifacts/new-graphics-compile" \
  JOBS=4 bash scripts/check-decatf-graphics-build.sh
python3 tests/test-egl-probe.py
```

Use new evidence/build directories. The compile script mirrors sources into a
path without spaces and makes no boot image. The EGL host test additionally
requires host EGL/GLES2 development libraries and Mesa's software renderer.

## Concrete userspace boundary: framebuffer posting

The owner's preserved Motorola gralloc contains actual ioctl call sites for
`FBIO_TEGRA_SET_NVMAP_FD` and `FBIO_TEGRA_FLIP`. This is static binary evidence,
not a trace of calls on Linux 4.4. Proprietary files and disassembly stay private.
The existing 24-byte nvhost submission decoder addresses a different boundary;
it cannot make these framebuffer requests work.

| Original ARM32 framebuffer interface | Measured value | Current Decatf framebuffer |
|---|---|---|
| `SET_NVMAP_FD` | `0x40044640` | Absent |
| `FLIP` | `0x41044641` | Absent |
| `GET_MODEDB` | `0xc0084642` | Present, matching encoding |
| Window / three-window flip argument size | 84 / 260 bytes | Legacy structures absent |
| Flip completion id / value offsets | 252 / 256 bytes | Legacy structures absent |

Sources are the pinned
[Motorola-lineage header](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/include/video/tegrafb.h)
and [Decatf framebuffer](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/tegra/video/fb.c).
Decatf's overlay interface has different request numbers and structures;
aliasing a device node or reinterpreting its arguments will not bridge this gap.

Reuse the original Motorola framebuffer posting code as the compatibility
reference while retaining Decatf's existing engine/allocator/DC implementations.
Do not copy its entire old `fb.c`: it would discard newer framebuffer behavior
and retains unresolved bounds/lifetime issues. Specific required adaptations:

1. Original window coordinates are integers; Decatf's DC window coordinates
   are `fixed20_12`. Reuse its existing conversion conventions and reject
   overflow. The overlay structure also places `flags` differently.
2. Adapt to Decatf's window-indexed DC syncpoint functions and existing extended
   wait API. Check pre-render waits before changing scanout. Reserve and report
   completion consistently with real display completion; never signal success
   immediately as a substitute for a completed flip.
3. Validate window indices, duplicates, supported formats, crop/stride/plane
   offsets and the complete pinned allocation extent before queueing a flip.
   The old source explicitly leaves surface bounds unchecked.
4. Keep imported nvmap references pinned through scanout. Drain work before
   freeing clients/buffers on release, errors and device removal. The original
   unregister ordering frees resources before draining work and cannot be
   copied unchanged. Fault-test partial pinning and all unwind paths.

These compatibility handlers are **not implemented** in this checkpoint.

## Offscreen rendering test prepared

`diagnostic/egl-probe/` is an optional Android build module using existing
EGL/GLES2 APIs. It creates only a 16×16 pbuffer, compiles two shaders, draws a
triangle in two different color frames, and checks center/background readback.
It requires NVIDIA/Tegra identity and an ES2 version string. A software renderer
is rejected. It opens no block device, mounts nothing and changes no display
mode or on-disk Android files. It is not installed in any automatic boot path.

Thirteen host cases exercise the actual client with Mesa software rendering,
test-only NVIDIA identity wrappers and injected setup/shader/link/draw/readback
failures. All pass, including rejection of genuine software identity, missing
draws and stale second-frame pixels, with resource cleanup checked. The test
wrappers are not linked into the Android module. This proves host client/test
behavior, **not Tegra execution**. The Android module has not yet been built
against the matching Android tree or run on the Xoom.

A successful device result would establish bounded offscreen rendering with
that kernel/library combination. It would not establish framebuffer posting,
asynchronous fences, HWC composition, stability or performance. Its 20-second
alarm bounds ordinary userspace stalls; a stuck uninterruptible driver wait
may still require the established recovery procedure.

## Next patches and hardware gates

| Stage | Separate change | Required check before advancing |
|---|---|---|
| G1 — complete offline | Patches 0071–0074 and reproducible full link | Real Kconfig exclusivity; generic/Samsung call guards; original tested profiles unchanged |
| G2 — pending | Separate Motorola legacy resource profile using Decatf's bindings | Check original carveouts, framebuffer ranges, GART ownership, IRAM reset-vector exclusion and each clock/reset dependency; no guessed Samsung values or unvalidated DVFS |
| G3 — pending | Optional Motorola framebuffer compatibility path reusing existing posting code | ARM32 ABI, bounds/overflow, pin/unpin lifetime, wait failures, queue teardown and completion tests; full ARM link with compatibility on/off |
| G4 — pending | RAM-only matched Motorola EGL/gralloc/HWC0 overlay and Android-built probe | Dependency closure, non-NEON target build, loader selection; no proprietary redistribution or system writes |
| G5 — pending | Boot-only resource/allocator smoke test with original restoration | Fresh USB report, correct nodes/resources, bounded allocate/map/cache/share/free checks; no engine submission until those pass |
| G6 — pending | Offscreen EGL, then framebuffer/HWC integration | NVIDIA identity plus correct repeated render/readback, real synchronization/error handling, then accelerated Welcome/lockscreen; restore and verify originals after each test |

Pbuffer creation may itself require a usable legacy framebuffer in this blob
set; it has not been demonstrated independent of G3. Do not bypass that
dependency by treating a failed probe as proof of a GPU engine fault.
The first integration should retain the installed KitKat HWC0 path. Decatf's
later HWC wrapper is available for a later framework migration; it is not a
prerequisite for the original Motorola KitKat HAL.

## Local source integrity incident

An empty loose Git object and an empty exported patch were detected after a
turn boundary. Their cause is unknown. The worktree was preserved; damaged
metadata was quarantined privately, the small MC exclusion correction was
recommitted as `a41e846e`, and patch 0074 was regenerated with flushed writes.
Current HEAD connectivity checks and the full build passed. This incident
does not establish a hardware failure and did not involve the device or its
backups. The superseded damaged commit is not a valid source/build identity.
