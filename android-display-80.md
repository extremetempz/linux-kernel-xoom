# Display power candidate 80 — built, not flashed

26 October 2026. Opt-in stage A/B display power work on top of the
hardware-tested battery79/78 image. **No suspend, wake, DVFS or charging
control is enabled.** No device operation was performed by this build.

## Definite correction found and fixed

KitKat's native LightsService opens all eight light IDs and later calls every
slot without a NULL check. The MR's adapter returned `ENOSYS` for keyboard,
buttons, battery, notifications, attention, Bluetooth and Wi-Fi, leaving seven
NULL pointers. A charger/battery or notification light update could therefore
crash system_server.

The adapter now opens all eight IDs. Only `backlight` performs hardware I/O;
the other seven are accepted no-ops. Unknown IDs still return `ENOSYS`.
A duplicate `CONFIG_SUSPEND` line in the displaypm defconfig was also removed.

## Image

- Path: `artifacts/display80-ready/wingray-android44-gpu.img`
- Size: 4,145,152 bytes
- SHA-256: `3847ee00eacbfd66177355c2f46ecdd606dc91705483882f7f167e09a93dc2ca`
- Kernel donor head: `3be7bf77`
- Profile: battery79 + Bluetooth + Wi-Fi + GPU/display + opt-in LP8550/DC
  blank path + KitKat backlight lights HAL
- **Not flashed or hardware validated**

## What the display path now does

On screen off, Android's LightsService requests brightness zero:

1. HAL writes `0` to `/sys/class/backlight/lcd-backlight/brightness`.
2. HAL sends `FBIOBLANK(4)` to `/dev/graphics/fb0`.
3. Kernel sets LP8550 to standby/zero brightness.
4. Kernel calls `tegra_dc_disable()` after backlight off.

On screen on:

1. HAL sends `FBIOBLANK(0)`.
2. Kernel re-enables DC and waits for scanout completion.
3. Kernel re-enables LP8550 and restores the saved brightness.
4. HAL writes the new brightness.

No SurfaceFlinger restart or framework replacement is involved.

## Offline validation

```text
actual fb/LP8550 callback sequencing and ten software cycles
actual KitKat lights ABI, all IDs, IO fault paths
compiled displaypm DT/config isolation
battery monitor, CPCAP, Bluetooth, Wi-Fi regressions
full ARM kernel, modules, lights HAL, DT and boot-image build
```

The image is under the fastboot limit. Hardware loading of the new HAL, visible
backlight extinction, DC power-down/resume, touch after resume, Wi-Fi/BT after
display cycles and repeated blank/unblank remain **physically unvalidated**.

## Test after explicit flash approval

Preserve 79/78 and recovery first. Flash only the boot image:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/display80-ready/wingray-android44-gpu.img
fastboot reboot
```

Then:

- **Test A:** run `/bin/display-backlight-cycle --run-backlight-only`; observe
  ten fully dark intervals and brightness restoration. Stop if brightness zero
  does not extinguish the light.
- **Test B:** press the physical power button off/on at least ten times,
  including rapid pairs. Confirm the screen is actually dark while off, the
  same Android session returns, and touch/GPU/Wi-Fi/BT/battery still work.
- Capture a report with `scripts/capture-framed-diagnostic.py`; inspect
  `P3 backlight requested/effective/power/fb/ret` and `Wingray display off/on`
  logs.

Do not write `mem` or attempt suspend. Stage 80 has no PM/suspend support and
no validated hardware wake source. If display recovery fails, use the
preserved 79/78 image; do not modify recovery or partitions.
