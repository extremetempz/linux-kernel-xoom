# Image 28: visible RGB scanout and guarded P3 backlight

Prepared 22 October 2026. Objective: get closer to a real Android lockscreen by
proving the minimum display path while retaining verified USB and BigPart.
This is a RAM diagnostic with color bars, not Android or a simulated lockscreen.
This preparation record is retained for provenance. The physical test failed the display gate; see trace-boot-attempt-28.md for measured results and restoration.

## Source and image

The donor remains Decatf Linux 4.4.147 at the pinned base plus the existing patch
series. New corrections are separate donor commits:

- `bfebb737`, patch 0046: guard P3 LP8550 current control by board/compatible,
  chip ID FC, mandatory power supply and recorded A1–A7 production settings.
  Use A0/current and control 01 only. Preserve Motorola's brightness scaling
  `(min(brightness,255) * 726) / 1000`, maximum code 185. Zero selects control
  04; nonzero selects 03. No A1–A7/EEPROM programming. Errors propagate and
  supply references balance on probe failures. Read-only register metadata
  uses the bound driver's backlight update lock.
- `16b70590`, patch 0047: isolated `wingray_display_defconfig` and DT. Keep the
  tested UP, no-L2, USB/PHY, GPIO dependency, eMMC/BigPart and PB2 shared-supply
  configuration. Add only DC0 RGB, the production AUO 1280×800 timing, captured
  display pin groups, P3 backlight and 16 MiB CMA. GPU engines, DC1, HDMI,
  touch, networking, PMIC/CPU-rail, CPU frequency and suspend remain disabled.
  Use the working non-LTE board's nominal 598 MHz PLL_C parent assignment.
  The prior measured 26 MHz reference permits that value in the PLL driver's
  integer calculation. Actual rate and scanout still require hardware evidence.

Kernel release `4.4.147-wingray-display`, cookie `0x584d001c`.
Image SHA-256:
`fc59bea179a560cfccfc7b329d0caa80cc1172caf499b7cf249b7ed4b66949a0`.
Image size 2,576,384 bytes; Android v0 header retains the measured working
load addresses `0x10008000`, ramdisk `0x11000000`, tags `0x10000100`, page 2048.
Appended DTB, gzip payload, fixed decompression destination, component layout
and header checksum passed the offline audit. These declarations alone do not
prove live bootloader register state; prior USB/storage boots provide separate
physical handoff evidence.

## Instrumentation and offline checks

The kernel and DT compile. Compiled config/DT/symbol checks pass. The verifier
was corrected to check the actual symbol `tegra_dc_rgb_init` rather than an
invented shortened name; no source change was needed for that verifier failure.

A tiny static ARMv7/VFPv3-D16 program opens only `/dev/fb0`, validates the exact
1280×800 packed 32-bit RGB layout and all mapped bounds, reapplies the existing
validated mode through fbdev, and draws eight vertical bars. Reapplying is
necessary because this minimal profile has no fbcon to trigger mode setup.
It changes no timings, opens no MMIO/block device and writes no persistent
state. The kernel chooses the framebuffer allocation; GART remains disabled.
The program re-reads and validates layout after mode application. Its printed
success means the drawing completed, not that a human saw scanout. Kernel DRM
logs, actual clock/connector/backlight metadata and operator observation are
required to establish visible success.

The display starter runs once in parallel with the USB server and waits at most
15 seconds for fb0. A blocked display ioctl therefore does not hold up the USB
server process. Fresh reports read metadata and the bound driver's twelve
register values; they never issue raw/forced I2C commands. The old raw panel-bus
helper is excluded when the display driver owns that address. Requests remain
strict PING/REPORT with nonce, length and SHA-256 verification.

Passed checks: actual backlight functions under UBSan with strict scope gates,
eight read failures/mismatches, all 256 brightness values and write failures;
actual framebuffer validation/drawing under ASan/UBSan with 21 invalid layouts,
RGB orders, alpha, offsets, padded stride and guard bytes; five actual startup/
report fixture controls; nine USB framing/storage regressions and six panel-bus
regressions. Static ELF has no interpreter/shared dependencies, undefined
symbols or NEON attribute. These host checks are not target runtime tests.

## Physical acceptance and restoration

Fresh preflight checks the exact original Wingray, completed Android boot,
wall power and battery, complete original boot/recovery bytes, and live disk/
all-ten-partition references. Flash only boot under the standing authorization.
Collect two independent fresh USB reports. Require retained full capacity and
all ten extents, no Android block mounts, expected LP8550 production bytes and
bounded current, connected 1280×800 display, nonzero DC IRQs/clock enable counts,
and an operator description of the visible image. Missing or failed items stay
explicit; no blind MMIO or raw I2C workaround is allowed.

Restore the original boot image regardless of display outcome. Read back and
compare both complete boot and recovery partitions after original Android
returns. Recovery, layout, system/cache/data and reserved RAM stay untouched.

## Route to the lockscreen

The installed working ROM is Android **4.4.4**, not evidence of a 6.0/8.1 image.
Read-only binary inspection found `gralloc.default.so`, the legacy NVIDIA HALs
and `libGLES_android.so`. That software renderer exposes GLES 1.x calls and no
exported shader-creation calls. The installed compositor imports both GLES1
and GLES2; imports alone do not establish which runtime path will work.

The pinned AOSP 4.4.4 sources provide a possible software route: RenderEngine
selects GLES10/11 or GLES20 based on the selected EGL config, Loader has an
explicit software-emulator path and normally skips libGLES_android in wildcard
driver discovery, and default gralloc falls back when double buffering is
rejected. This is source context, not a tested claim about the installed ROM's
exact implementation. Changing a filename or finding a library is insufficient.
Android framework/HWUI acceleration, native buffer formats, fences, gralloc
selection and EGL config must all be checked. Do not globally claim emulator
hardware or expose old NVIDIA ioctls merely to make discovery succeed.

After visible scanout, enable only Android kernel prerequisites (correct legacy
32-bit Binder ABI for the installed ROM, ashmem, cgroups and required logging),
then test graphics services with USB logs before starting framework. Adapt RAM
init/fstab/device-node paths to this DT kernel. Prefer a read-only system and
RAM-backed first-boot data/overlays so the working installation is preserved.
Any need to write existing Android storage must be made concrete before use.
Wi-Fi, audio, camera, suspend and acceleration are deferred until the real
lockscreen; touch follows the display path if needed to operate it.

Primary source context: [AOSP RenderEngine](https://android.googlesource.com/platform/frameworks/native/+/android-4.4.4_r2/services/surfaceflinger/RenderEngine/RenderEngine.cpp),
[AOSP EGL Loader](https://android.googlesource.com/platform/frameworks/native/+/android-4.4.4_r2/opengl/libs/EGL/Loader.cpp),
[AOSP default framebuffer allocator](https://android.googlesource.com/platform/hardware/libhardware/+/android-4.4.4_r2/modules/gralloc/framebuffer.cpp).
The exact tagged source files were fetched and inspected locally; runtime
libraries, raw reports and original images remain private ignored artifacts.
