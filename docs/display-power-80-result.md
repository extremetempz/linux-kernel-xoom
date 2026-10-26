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

## DC rollback

The later sysfs HAL made Android actually disable the DC. Every log said
`dc=1` after re-enable, but the panel stayed dark with a scan line — both on
Android cycles and on FBTEST. The DC disable/enable sequence is therefore not
a valid panel power-down for this board. It has been rolled back to
backlight-only. See [DC rollback](display-power-80-dc-rollback.md).

## Root FBTEST result

The fixed root FBTEST proved the kernel side works:

```text
FB_BLANK_WRITE4_RC 0
[92.442517] tegradc tegradc.0: Wingray display off: blank=4 dc=0
FB_BLANK_WRITE0_RC 0
[93.737144] tegradc tegradc.0: Wingray display on: dc=1
```

`fb0/state` stayed 0, so it is not authoritative. The missing piece was the
Android HAL path. The next diagnostic image uses the same sysfs blank route
and grants the system user/group write access.

## Host-vs-tablet command note

The attempted `echo 4 > /sys/class/graphics/fb0/blank` was run on the Ubuntu
host (`justin@justin-VMware-Virtual-Platform`), not on the tablet. Its
`/sys/class/graphics/fb0` is the host VM framebuffer, the write is denied, and
host `dmesg` is restricted. It says nothing about the Xoom.

The tablet's `/dev/ttyACM0` diagnostic gadget is **not a shell**. Its
`diagnostic/server.sh` accepts only fixed `PING <nonce>` and `REPORT <nonce>`
frames; arbitrary commands are deliberately ignored. The current image
therefore has no interactive USB root console for this sort of manual sysfs
test.

To settle DC blanking, either use the physical `ttyS0` UART console (115200)
or add a fixed, bounded `FBTEST` request or one-shot diagnostic service to a
new opt-in image. The latter should write `4` then `0` to
`/sys/class/graphics/fb0/blank`, read `fb0/state`, and capture
`dmesg | grep Wingray`. No arbitrary shell is needed. Do not treat the host
permission error as a display failure.
