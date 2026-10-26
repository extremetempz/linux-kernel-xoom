# Display 80 — DC blank rollback

27 October 2026. The DC blank/unblank path passed its software tests and the
root FBTEST proved it could switch `dc=0`/`dc=1`, but the physical panel did
not return after re-enable. The symptom was a dark screen with a single scan
line; Android's own power-button cycles showed the same result.

## Evidence

Root FBTEST:

```text
Wingray display off: blank=4 dc=0
Wingray display on: dc=1
```

Android cycles at 121–132 s also logged four off/on pairs. After each reported
`dc=1`, the panel remained dark/line. `fb0/state` stayed 0 and is not a
reliable indicator.

## Conclusion

`tegra_dc_disable()` / `tegra_dc_enable()` is not a sufficient panel power
sequence for this P3 AUO panel. Re-enabling the controller, windows, clocks and
LP8550 does not restore visible scanout. A correct DC power-down requires the
panel reset/power sequencing and delay details that are not established yet.

The safe choice is therefore:

- keep the display controller running;
- blank only the LP8550 backlight;
- do not use DC power-down in the Android blank path;
- keep Stage 3 suspend gated.

This loses the DC power saving but preserves a reliable dark screen and
wake-up. The visible screen is genuinely dark because the LEDs are off; it is
not a black framebuffer.

## Code change

`tegra_fb_wingray_blank()` now calls only
`tegra_wingray_backlight_power()`. It logs:

```text
Wingray backlight off: DC left enabled
Wingray backlight on
```

The HAL still writes `fb0/blank`; the fb path maps that to backlight-only.
FBTEST is retained as a bounded backlight transition test, not a DC test.

## Recovery confirmed

The backlight-only image (`display80fbtest5`, SHA-256 `02ab70c2595f…`) was
flashed on 27 October 2026. Power off/on works, the panel returns without a
line, and the DC remains at `dc=1` throughout. See
[Test 5 result](display-power-80-test5-result.md).

Do not re-enable DC blank until the panel reset/power sequence has hardware
evidence.
