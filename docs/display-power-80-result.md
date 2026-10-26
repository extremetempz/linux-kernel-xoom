# Display 80 — Test A/B hardware result

26 October 2026. Report:
`artifacts/androiddisplay80-report/report-private.txt` (integrity verified;
the wrapper's `state: failed` is the pre-existing filesystem-path validator).

## Passed: LP8550 backlight off/on

The user pressed the power button off/on ten times and confirmed the screen
became fully dark and brightness returned each time. The log shows repeated
zero and restore transitions:

```text
P3 backlight requested=0  effective=0  power=0 fb=0 ret=0
P3 backlight requested=79 effective=79 power=0 fb=0 ret=0
P3 backlight requested=0  effective=0  power=0 fb=0 ret=0
P3 backlight requested=79 effective=79 power=0 fb=0 ret=0
...
```

Eight zero transitions are visible in the captured tail, interleaved with
the CPCAP power-key press/release events. The session, GPU, touch, Wi-Fi,
Bluetooth and battery monitor remained alive; there was no framework restart.

This validates the LP8550 brightness-zero path and the restored brightness.

## Not proven: display-controller blank/power-down

At every zero transition the backlight log still reports:

```text
power=0 fb=0
```

and the report contains **no `Wingray display off` / `Wingray display on`
messages**. The Stage 80 helper sets `bl->props.power=FB_BLANK_POWERDOWN` and
disables the DC when `FBIOBLANK` reaches `tegra_fb_wingray_blank`; neither is
evidenced here.

The observed behaviour is therefore consistent with **only LP8550 brightness
being set to zero**, while the display controller remains enabled. The screen
is visibly dark because the LEDs are off, but DC power-down and resume are not
validated.

Likely remaining causes:

- the HAL's `FBIOBLANK` cannot open/write `/dev/graphics/fb0` as system_server;
- the ioctl fails and the HAL's error is not surfaced in the captured logs;
- `display_blanked` state suppresses the ioctl after an earlier failed
  transition;
- the `wingray_backlight` binding is not reaching the helper.

`/sys/class/graphics/fb0/blank` is write-only in this kernel (`show_blank`
returns 0), so the empty report field is expected and is not evidence.

## Next diagnostic, no new image

From the diagnostic root console, while the screen should be off:

```sh
echo 4 > /sys/class/graphics/fb0/blank
cat /sys/class/graphics/fb0/state
dmesg | grep -E 'Wingray display|tegra_fb|fb_blank'
echo 0 > /sys/class/graphics/fb0/blank
```

If this prints `Wingray display off/on`, the kernel path works and the Lights
HAL's fb0 open/ioctl is the failing link. If it fails here too, the kernel
blank path or fb0 permissions are the problem. Do not enable suspend until
this is resolved.

## Status

- Backlight zero and restore: **hardware-validated**
- Android power-key off/on: **hardware-validated**
- Display-controller blank/unblank: **not proven**
- Suspend/deep sleep: **not implemented**
