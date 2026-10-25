# Image 66: fixed screen-awake service and interim volume wake key

25 October 2026. Image 65's screen-awake service never ran. Its report shows:

```text
init: /init.xoom-awake.rc: 6: invalid service name 'xoom-screen-awake'
```

Android init service names cannot contain hyphens. The service therefore
failed to parse, `/run/xoom-screen-awake.log` was never created, and the
120-second timeout still blanked the panel with no wake source.

## Changes in Image 66

- Rename the init service to `xoom_screen_awake`. The executable remains
  `/bin/xoom-screen-awake`.
- The boot-completed service now sets `screen_off_timeout` to the maximum,
  enables `stay_on_while_plugged_in=7`, runs `svc power stayon true`, retries,
  and logs readback to `/run/xoom-screen-awake.log`.
- Re-add the physical volume GPIO keys in the fixed-clock GPU base DT, with
  `wakeup-source`, and enable `CONFIG_INPUT_KEYBOARD`/`CONFIG_KEYBOARD_GPIO`.
- Map **volume-down** to `KEY_POWER` so it can act as a physical interim wake
  key. Volume-up remains a volume key.
- Add `dumpsys gfxinfo` output for Trebuchet and SetupWizard to the display
  report for the next performance measurement.

The real Xoom power button is a **CPCAP PMIC interrupt**, not a GPIO. Porting
the CPCAP key/IRQ driver is still required for the actual power button. Image
66 does not claim that work is complete.

## Image identity

- Path: `artifacts/androidgpu66-ready/wingray-android44-gpu.img`
- Size: 3,651,584 bytes
- SHA-256: `37956a4d758f28406bb32d498f993160e27dda16184a2f1b031b6c95e360ef6a`
- Source patch: `0115-wingray-interim-volume-wake.patch`

The DTB contains the two `gpio-keys` entries and the shared keypad-column hog.
The service name in `init.xoom-awake.rc` is `xoom_screen_awake`.

## Test

Flash boot-only:

```sh
fastboot flash boot artifacts/androidgpu66-ready/wingray-android44-gpu.img
fastboot reboot
```

Verify:

1. The display remains on beyond two minutes.
2. `/run/xoom-screen-awake.log` shows successful readback.
3. `dumpsys power` shows `mScreenOn=true`, `mWakefulness=Awake`.
4. Touching the UI still works.
5. Pressing **volume-down** sends a power-key event; if Android blanks, press
   it again to wake.
6. The report's `/proc/bus/input/devices` contains a `gpio-keys` device.

Capture after interacting:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu66-report1 \
  --storage-mode android44-readonly
```

The report includes `XOOM_SCREEN_AWAKE`, `XOOM_GFXINFO`, input devices and the
usual display/GPU state.

## Not included

These are separate, larger milestones and are **not** claimed by Image 66:

- actual CPCAP power button / PMIC wake source;
- Wi-Fi (BCM4329/bcmdhd firmware and Android supplicant service);
- Bluetooth (BCM4329 UART/power/firmware);
- battery, charging and fuel-gauge reporting (the current kernel has no
  power_supply driver, hence the 0% battery);
- suspend/resume and complete power management.

Those require dedicated driver ports and hardware validation rather than
configuration toggles. They should be developed as separate images.
