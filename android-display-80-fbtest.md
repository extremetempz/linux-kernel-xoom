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

- Path: `artifacts/display80fbtest3-ready/wingray-android44-gpu.img`
- Size: 4,147,200 bytes
- SHA-256: `2d0b16dbd2875c0b8628b1dfa513272de559d7742471b64969403bffe7b4e9ba`
- Kernel donor head: `e038c692`
- Profile: display80 plus fixed FBTEST helper and sysfs-blank lights HAL
- **Not flashed or hardware validated**

The earlier FBTEST image (`2672682f…`) proved the kernel path but showed that
Android was not reaching it. This rebuilt image changes the HAL to use the
same `/sys/class/graphics/fb0/blank` path that the root test proved, and grants
the system user/group write access in the opt-in display profile.

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

Before running it, press the physical power button off and on once. Then the
captured dmesg should contain:

```text
Wingray display off: blank=4 dc=0   # from the Android power-button cycle
Wingray display on: dc=1
Wingray display off: blank=4 dc=0   # from the manual FBTEST
Wingray display on: dc=1
```

`fb0/state` is not authoritative for every blank transition; the decisive
evidence is the `Wingray display off/on` dmesg pairs. If only the LP8550
`power=4`/brightness lines appear, the HAL is still not invoking the sysfs
blank path.

## Safety

- FBTEST performs only the two documented fb0 blank writes and always attempts
  unblank restoration.
- No suspend, PMIC, charger, voltage, GPIO export or arbitrary shell path.
- Do not run during critical storage writes.
- Preserve the working 79/78 image and recovery; never write recovery or
  partitions.
