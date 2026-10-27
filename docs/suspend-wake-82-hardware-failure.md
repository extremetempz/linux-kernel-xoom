# Suspend preparation 82 — awake IRQ hardware failure

27 October 2026. The wakeirq test image was flashed after the offline review.
The power button initially worked, but on turning the screen off the tablet
could not be woken again. The USB diagnostic gadget disappeared completely,
so no report or dmesg could be captured. A reboot restored the device; a
second screen-off attempt reproduced the same loss of wake/USB.

This is a **hard failure of the awake IRQ test profile**, not deep sleep: the
wakeirq profile has CONFIG_PM/SUSPEND disabled. The failure could be in the
new LIC/regmap ON path or in the candidate 81 DC blank/resume path that this
profile inherits; the missing log prevents separating them.

## Status

- IRQ-only profile: **failed hardware wake test**
- Polling removal: not validated on hardware
- LIC routing: not validated on hardware
- Candidate 81 display path as included here: not stable enough for daily use
- Suspend/deep sleep: **must not be attempted**
- No root cause is claimed without the lost log

## Recovery

Use the validated Test 5 backlight-only image; it does not enable DC
power-down or the IRQ-only path:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/display80fbtest5-ready/wingray-android44-gpu.img
fastboot reboot
```

Candidate 81 remains an alternative hardware-tested display image, but Test 5
is the conservative fallback after this failure.

The wakeirq image must not be flashed again until the failure is captured and
the IRQ and DC paths are tested separately. Android screen-off is not suspend;
the observed hang must not be mistaken for a suspend result.
