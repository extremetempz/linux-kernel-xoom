# Display 80 FBTEST diagnostic image — built, not flashed

26 October 2026. A second opt-in display image adds a fixed USB diagnostic
request because the tablet has no interactive USB root shell and no physical
UART console is available.

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

- Path: `artifacts/display80fbtest-ready/wingray-android44-gpu.img`
- Size: 4,149,248 bytes
- SHA-256: `2672682ff35e394a91b383157ea6f8aba803e9a0e29ae2a78637676e18e83dbf`
- Kernel donor head: `3be7bf77`
- Profile: display80 plus fixed FBTEST helper
- **Not flashed or hardware validated**

This is a diagnostic image, not a new display-power feature. The known-good
display80 backlight test image remains
`artifacts/display80-ready/wingray-android44-gpu.img`.

## Run it

Flash only this diagnostic boot image after retaining the working 78/79
images and recovery path:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/display80fbtest-ready/wingray-android44-gpu.img
fastboot reboot
```

From the host, once the tablet has booted:

```sh
python3 scripts/run-fb-blank-test.py \
  --output-dir artifacts/display80-fbtest1
```

The screen may go dark for about one second. The command prints the captured
state/log and saves `fb-blank-test.txt`.

Expected if the kernel DC path works:

```text
FB_BLANK_STATE_BEFORE 0
FB_BLANK_STATE_OFF 1
Wingray display off: blank=4 dc=0
FB_BLANK_STATE_ON 0
Wingray display on: dc=1
```

`fb0/state` is not authoritative for every blank transition; the decisive
evidence is the `Wingray display off/on` dmesg pair. If only the LP8550
`power=4`/brightness lines appear, the `FBIOBLANK` path is still not reaching
the DC helper.

## Safety

- FBTEST performs only the two documented fb0 blank writes and always attempts
  unblank restoration.
- No suspend, PMIC, charger, voltage, GPIO export or arbitrary shell path.
- Do not run during critical storage writes.
- Preserve the working 79/78 image and recovery; never write recovery or
  partitions.
