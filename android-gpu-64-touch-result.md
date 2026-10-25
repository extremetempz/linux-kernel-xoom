# Image 64 result: touch and three-finger input verified

25 October 2026. Image 64 booted with the visible Android UI and a verified
USB report containing real evdev input during the five-second observation.

- Image: `artifacts/androidgpu64-ready/wingray-android44-gpu.img`
- SHA-256: `36ae3d235e76888802676e21adbf661a6562a94bdebecb2b402269549aef1207`
- Report: `artifacts/androidgpu64-report2`
  SHA-256 `a523fc978e57b69ca2924922e9fbbcecd1b691e6313d99c80b1531b899db6e26`
- Operator confirms the visible UI responds to touch.

## Verified input

- Device: `/dev/input/event0`, `Atmel maXTouch Touchscreen`, `i2c-0-005b/input0`.
- 2,277 input events over 188 frames.
- 25 presses, 22 releases, 840 position events, 0 invalid events.
- Three simultaneous contacts were observed:
  - slot 0, id 25, x 1306–1422, y 621–1304
  - slot 1, id 26, x 1030–1178, y 563–1217
  - slot 2, id 27, x 796–909, y 736–1382
- maXTouch IRQ 225 advanced from 977 to 1,169 during the sample.
- Coordinates are within the reported ranges (X 0–2580, Y 0–1630).

## Display and composition

- SurfaceFlinger still reports NVIDIA Tegra OpenGL ES 2.0 and NVIDIA gralloc.
- HWC present/enabled with `numHwLayers=0`: composition remains GPU/client
  target, not HWC overlay composition.
- DC window A `DC_WIN_WIN_OPTIONS=0x40000000`; no underflows.
- No `NvGrPost`/`FBIO_TEGRA_FLIP` errors.
- `sys.boot_completed=1`; storage geometry and read-only policy match.

## Stability observations

- No tombstones, kernel panic, Oops or fatal input errors.
- `MemTotal=738436 kB`, `MemFree=169652 kB`, `MemAvailable=336984 kB`.
- The pre-existing `gpiochip_add`/sysfs warning at 0.017 s remains; it is not
  a display or input failure.
- `last eglSwapBuffers()` was 27.689 ms in the post-interaction snapshot.
  This is a single sample taken during report generation, not a frame-rate
  benchmark; performance remains to be measured properly.

## Remaining work

- Complete the setup wizard and verify the launcher/lockscreen.
- Measure sustained UI frame pacing and decide whether HWC overlay composition
  is practical.
- Understand the 66.25 MHz PLL_C/disp1 rate versus the 598 MHz Image 29 path.
- Restore and verify the original boot/recovery after testing.
- Evaluate Wi-Fi, Bluetooth, audio, charging, sensors and power management.
