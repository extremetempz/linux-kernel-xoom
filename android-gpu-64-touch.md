# Image 64 diagnostic: record touch interaction with the visible UI

25 October 2026. Image 64 is Image 63 plus the read-only touch report enabled
for the `-gpu` release. The kernel, DTB, config and display behavior are
unchanged. It is a test-tooling image, not a new display fix.

- Path: `artifacts/androidgpu64-ready/wingray-android44-gpu.img`
- Size: 3,637,248 bytes
- SHA-256: `36ae3d235e76888802676e21adbf661a6562a94bdebecb2b402269549aef1207`
- `touch-report.sh` now accepts `4.4.147-wingray-android44-gpu` and runs the
  existing bounded five-second evdev observer.

## Test

Flash boot only. After the setup wizard is visible, start the report capture
and immediately tap/drag repeatedly on the screen for at least ten seconds;
the five-second observer runs near the end of the report:

```sh
fastboot flash boot artifacts/androidgpu64-ready/wingray-android44-gpu.img
fastboot reboot

python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu64-report1 \
  --storage-mode android44-readonly
```

The report should contain `XOOM_TOUCH_EVENTS` with presses, releases and
position events from `Atmel maXTouch Touchscreen`. If no events are captured,
repeat the capture while touching; no reflash is needed.

## Expected outcome

- Touch events and coordinates from the visible setup wizard.
- `/proc/interrupts` maXTouch count advances.
- The UI responds to taps/drags (operator observation).
- Existing GPU composition, backlight, storage, USB and two-core behavior
  remain unchanged.

This image does not add Wi-Fi, audio, charging, DVFS or suspend support.
Original boot/recovery restoration is still pending after the test.
