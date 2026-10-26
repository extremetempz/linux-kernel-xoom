# Display 80 FBTEST diagnostic image — built, not flashed

26 October 2026. A second opt-in display image adds a fixed USB diagnostic
request because the tablet has no interactive USB root shell and no physical
UART console is available.

## Root-path result already proven

The first FBTEST run returned:

```text
FB_BLANK_WRITE4_RC 0
FB_BLANK_STATE_OFF 0
[   92.442517] tegradc tegradc.0: Wingray display off: blank=4 dc=0

FB_BLANK_WRITE0_RC 0
FB_BLANK_STATE_ON 0
[   93.737144] tegradc tegradc.0: Wingray display on: dc=1
```

So the kernel DC blank/unblank path works. `fb0/state` remains 0 on this
driver and is not authoritative; the `Wingray display off/on` messages are.
The Android power-button path did not produce those messages, so the HAL was
still not invoking the blank path. This image addresses that by using the
already-proven sysfs route.

## What is new

`FBTEST <nonce>` is an additional fixed request in the existing diagnostic
server. It is not a shell. The root helper:

1. reads `/sys/class/graphics/fb0/state`,
2. writes `4` to `/sys/class/graphics/fb0/blank`,
3. waits one second and captures the display-related `dmesg`,
4. writes `0` back,
5. captures the resumed state/log,
6. always attempts unblank restoration via an `EXIT/HUP/INT/TERM` trap.

The result is SHA-256 framed on the same USB ACM gadget as `PING`/`REPORT`.
No arbitrary command is evaluated.

## Image identity

- Path: `artifacts/display80fbtest5-ready/wingray-android44-gpu.img`
- Size: 4,149,248 bytes
- SHA-256: `02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`
- Kernel donor head: `f61aaf75`
- Profile: display80 plus FBTEST, sysfs blank HAL and backlight-only fb blank
- **Hardware-validated** on 27 October 2026: power off/on works, backlight
  extinguishes and restores, and the DC stays at `dc=1`.

The DC blank experiment was rolled back after the panel failed to restore.
See [Test 5 result](docs/display-power-80-test5-result.md) and
[DC rollback](docs/display-power-80-dc-rollback.md).

The FBTEST image proved that Android can reach the blank path, but also proved
that disabling the DC leaves the panel dark with a scan line after re-enable.
This rebuilt image therefore keeps the DC running and blanks only the LP8550
backlight. The HAL uses the sysfs blank path, and the opt-in profile grants the
system user/group write access.

This is a diagnostic image, not a new display-power feature. The known-good
display80 backlight test image remains
`artifacts/display80-ready/wingray-android44-gpu.img`.

## Run it

Flash only this diagnostic boot image after retaining the working 78/79
images and recovery path:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/display80fbtest3-ready/wingray-android44-gpu.img
fastboot reboot
```

From the host, once the tablet has booted:

```sh
python3 scripts/run-fb-blank-test.py \
  --output-dir artifacts/display80-fbtest1
```

The screen may go dark for about one second. The command prints the captured
state/log and saves `fb-blank-test.txt`.

Before running it, press the physical power button off and on once. The screen
should go dark and return normally. Then FBTEST should show backlight-only
transitions:

```text
Wingray backlight off: blank=4 dc=1
Wingray backlight on: dc=1
```

The DC remains enabled. If the screen does not return, stop and report the
full FBTEST file; do not attempt DC power-down again.

## Safety

- FBTEST performs only the two documented fb0 blank writes and always attempts
  unblank restoration.
- No suspend, PMIC, charger, voltage, GPIO export or arbitrary shell path.
- Do not run during critical storage writes.
- Preserve the working 79/78 image and recovery; never write recovery or
  partitions.
