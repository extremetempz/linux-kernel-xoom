# Image 63 result: Android UI visible with NVIDIA GPU composition

25 October 2026. One boot-only test of
`artifacts/androidgpu63-ready/wingray-android44-gpu.img`
(SHA-256 `3e05f746656e53e12efce1b11b297fe9ffaa212d5e6b2592a3a16f82fc82adfa`)
completed. The operator confirms Android booted and the setup wizard is
visible. One fresh, nonce/integrity-verified USB report was captured at
`artifacts/androidgpu63-report1`.

## Verified on hardware

- Android reaches `sys.boot_completed=1`; the setup wizard, status bar,
  navigation bar and wallpaper layers are present and visible.
- SurfaceFlinger reports `GLES: NVIDIA Corporation, NVIDIA Tegra,
  OpenGL ES 2.0` and HWC present/enabled.
- `Nvidia Gralloc` is in use; `libEGL_tegra` and `libGLESv2_tegra` hashes are
  present in the checked system.
- No `NvGrPost: Failed, FBIO_TEGRA_FLIP` errors in the report.
- DC is in continuous display mode (`DC_CMD_DISPLAY_COMMAND=0x20`),
  `DC_WIN_WIN_OPTIONS=0x40000000` for window A, no underflows, DC IRQ 21
  advanced to 42.
- Backlight is registered at brightness 128, `bl_power=0`; LP8550 A1-A7
  match production values and A0=0x5c.
- `DisplayDevice` reports `flips=20`, 1280x800, and three layers.
- Storage geometry, both CPUs, PL310, touch, USB and the read-only Android
  policy remain intact.

## GPU acceleration qualification

The path is **GPU accelerated**: SurfaceFlinger renders with NVIDIA Tegra
OpenGL ES 2.0 and NVIDIA gralloc buffers, then posts the composed framebuffer
through gralloc/FBIO_TEGRA_FLIP to the Tegra DC.

It is **not hardware-overlay composition**: the HWC reports
`numHwLayers=0`, so SurfaceFlinger composites the visible layers on the GPU
into the framebuffer. The DC scans out that single full-screen window.
`numHwLayers=0` is therefore a composition-performance limitation, not a
software-rendering fallback. `last eglSwapBuffers() time` was 7480 us in this
snapshot; no frame-rate or overlay-performance conclusion is drawn from a
single sample.

## Remaining issues

- HWC overlay composition is not exercised; all composition is GPU/client
  target.
- Live PLL_C/disp1 is 66.25 MHz with shift divider 0, not the 598 MHz/divider
  16 path used by Image 29. The panel timing works, but the difference should
  be understood.
- Touch interaction, lockscreen, long-run display stability and performance
  have not been revalidated with this image.
- Original boot/recovery restoration has not been performed after this test.
- Wi-Fi, Bluetooth, audio, charging, DVFS and suspend remain outside this
  milestone.

## Preservation

The tested image and report are retained under the ignored `artifacts/`
directories. The original boot/recovery backups remain in
`artifacts/hardware-private`; restore and verify them before any unrelated
flash.
