# Image 63: fix legacy framebuffer z-order validation

25 October 2026. Image 62 established that the clock and backlight fixes work
and isolated the remaining blank-screen cause to Android framebuffer posting.

## Image 62 findings

- Operator saw the Motorola logo and then the RGB test pattern: physical
  scanout and backlight are working.
- `lcd-backlight` is registered at brightness 128, `bl_power=0`, and the LP8550
  registers are A1=0x67, A2=0xbf, A0=0x5c; the panel is lit.
- The DC is in `DISP_CTRL_MODE_C_DISPLAY`, with no underflows.
- `DC_WIN_WIN_OPTIONS` is zero: window A is disabled after the pattern.
- SurfaceFlinger is running with NVIDIA ES2 and HWC, but logcat repeatedly
  reports: `E/gralloc: NvGrPost: Failed, FBIO_TEGRA_FLIP Invalid argument`.
- Android's display power state is on (`mScreenOn=true`, `mScreenBrightness=102`).

## Root cause

The Motorola gralloc `NvGrPost` path fills `tegra_fb_windowattr.z` with
`layer index + 2` (2, 3, 4). `z` is a relative blend-order value consumed by
`tegra_dc_set_blending()`; it is not a DC window index. The compatibility
validator required `z < DC_N_WINDOWS`, so Android multi-layer posts were
rejected with `-EINVAL`. The framebuffer window was never updated/enabled,
leaving a lit but black panel after the pattern.

The original Motorola driver copies `z` into `win->z` without a window-index
bound. The DC blend code compares z values and does not index an array with
them.

## Patch 0114

Remove only the invalid `z >= DC_N_WINDOWS` check. All crop, format, stride,
alignment, pin-extent, 32-bit address and window-index checks remain. The host
framebuffer test now accepts z=3 as a legal blend order.

## Image identity

- Path: `artifacts/androidgpu63-ready/wingray-android44-gpu.img`
- Size: 3,637,248 bytes
- SHA-256: `3e05f746656e53e12efce1b11b297fe9ffaa212d5e6b2592a3a16f82fc82adfa`
- Kernel config and DTB are identical to Image 62; only code changed.

## Expected hardware result

- No `NvGrPost: Failed, FBIO_TEGRA_FLIP` errors in logcat.
- `DC_WIN_WIN_OPTIONS` enabled for the active Android window.
- The setup wizard/Android UI becomes visible.
- SurfaceFlinger/HWC/NVIDIA renderer and existing boot/storage/touch/USB
  behavior remain intact.

If posting still fails, the next report should use the display-report/logcat
data to identify the exact remaining attribute; no further blind bounds
changes will be made.
