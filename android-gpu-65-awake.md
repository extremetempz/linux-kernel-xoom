# Image 65: keep the display awake until a power-key wake path exists

25 October 2026. Image 64 exposed a usability dead end: Android's 120-second
screen timeout turns the panel off, but this kernel has no power-key input
device and the touchscreen does not wake Android. Power and touch therefore
cannot recover the display.

The blank-screen report (`artifacts/androidgpu64-report4`) shows:

- `mWakefulness=Asleep`
- `mScreenOn=false`, photonic `mActualOn=false`, `mActualBacklight=0`
- `Going to sleep due to screen timeout...`
- `/proc/bus/input/devices` contains only the maXTouch touchscreen; no power-key
  input device is registered
- no panic, Oops or tombstone; the kernel and Android services remain alive
- `libsuspend` cannot use `/sys/power/state` or `/sys/power/autosleep`
  because suspend is disabled in this configuration

This is a missing wake-source problem, not a display-driver failure.

## Development workaround

Image 65 adds a one-shot init service started on `sys.boot_completed=1`:

- sets `screen_off_timeout` to `2147483647`;
- sets `stay_on_while_plugged_in=7`;
- runs `svc power stayon true` as a fallback;
- retries and logs results to `/run/xoom-screen-awake.log`.

This keeps the panel awake while the device is powered, so the UI remains
usable. It is a development workaround, not a final power-management design.
A proper implementation should register the Xoom power key/PMIC wake source
and allow normal screen-off/suspend behavior.

## Image identity

- Path: `artifacts/androidgpu65-ready/wingray-android44-gpu.img`
- Size: 3,637,248 bytes
- SHA-256: `1061ee6a7843cf6b5de6ad45212bc999ad757ec5db8db5fb69976bcd84fb8c59`
- Kernel config and DTB are identical to Image 64; only the built-in Android
  runtime/service and display report changed.
- The display report now includes `XOOM_SCREEN_AWAKE` with the service log.

## Test

The current device is asleep and cannot be woken by power/touch. Reboot to
fastboot, flash boot only, and reboot:

```sh
fastboot flash boot artifacts/androidgpu65-ready/wingray-android44-gpu.img
fastboot reboot
```

After boot, confirm:

- the display remains on beyond two minutes;
- `/run/xoom-screen-awake.log` reports successful readback;
- `dumpsys power` reports `mScreenOn=true` and `mWakefulness=Awake`;
- touch still works;
- no display/posting errors.

If the settings service fails, the report log will identify the failing
command; do not treat the black screen as a display regression.

## Limits

- This image does not add suspend/resume or a power-key wake source.
- It does not add Wi-Fi, Bluetooth, audio, charging or DVFS.
- Original boot/recovery restoration remains pending after testing.
