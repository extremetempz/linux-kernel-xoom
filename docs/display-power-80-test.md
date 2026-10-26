# Display-power candidate 80 — stage A/B, never flashed automatically

Based on main c887905 / hardware-tested battery79. This is a separate opt-in
profile with new LP8550 power handling, explicit framebuffer sequencing and a
minimal KitKat lights adapter. **No PM/SUSPEND/DVFS or new wake source enabled.**
See [architecture and cause audit](display-power-suspend-audit-80.md).

## Build and preservation

```sh
XOOM_ANDROID_GPU_PROFILE=displaypm \
XOOM_BUILD_ROOT=/tmp/xoom-display80-clean \
XOOM_ARTIFACT_DIR="$PWD/artifacts/display80-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/display80-new-ready" \
bash scripts/build-android-gpu.sh
```

Use new directories. Build and pack scripts contain no device operations.
Private original-ROM inputs and known-good 78/79 images remain local. Before
any later manual test, retain complete original boot/recovery backups, hashes,
working 79 image and a verified fastboot restoration path. This document is
not authorization to flash, reboot or suspend the tablet.

Prepared image identity and tests are recorded in the manifest under
`artifacts/display80-ready`. Kernel source patches 0146–0148 are separate from
Android adapter/build/report changes. Stage80 is hardware-unverified.

## Offline evidence

- Targeted fb/DC/LP8550 ARM objects also compile with the new option disabled.
- New patches 0146–0148 apply after the reconstructed 145-patch battery series.
- Full ARM kernel/module build and Android image packing, built-in runtime
  consistency, appended DT and minimal shared lights HAL compile/ABI checks.
- Actual LP8550 callback tests for power/fb blank/suspend flags, preserved
  brightness and failed I2C result; no hardware LED-off inference.
- Actual framebuffer callback fault tests: backlight off before DC disable,
  DC/frame completion before backlight on, positive-jiffy success, timeouts,
  enable/update errors, safe failed-unblank state and ten software cycles.
- Actual lights adapter tests: RGB/zero values, fixed paths, denied/short/
  interrupted writes, framebuffer ioctl ordering/error propagation, all eight
  KitKat light IDs opened, non-backlight no-ops, unknown IDs rejected. ARM32
  HMI/device sizes checked against KitKat headers; no runtime dependencies or
  NEON.
- Compiled DT/config checks retain all existing board properties except adding
  the explicit backlight binding and opt-in marker. Suspend/CPU frequency
  remain off. Existing battery/Bluetooth/CPCAP/Wi-Fi gates pass.

These do not prove visible darkness, working Android HAL loading, physical
wake, electrical power savings or any actual suspend/resume cycle.

## Diagnostic collection

The normal framed report includes `/bin/power-report`. It reads sleep-state
availability, blockers/wakeup sources where exported, CPU state, backlight
settings, framebuffer state, interrupts, DS2781 measurements, display and
power dumpsys, and relevant logs. Missing PMC debugfs is explicitly reported;
there is no raw /dev/mem read while clocks might be off.

Owner logs distinguish `P3 backlight requested/effective/power/fb/ret` and
`Wingray display off/on dc=...`. Backlight `actual_brightness` may still reflect
the requested setting; it is not an optical measurement. DC software state
and successful register writes are not proof of power gating. An unavailable
/sys/power/state or PMC field is evidence to record, not a reason to invent it.

After an explicitly approved later flash, use fresh private report directories:

```sh
python3 scripts/capture-framed-diagnostic.py \
 --output-dir artifacts/display80-before --storage-mode android44-readonly
```

The existing storage-policy parser does not recognize all Wi-Fi RAM overlay
mounts and may report failed while report_integrity is verified. Do not
mislabel that as a storage-validation pass or bypass its checks. Save the raw
report and inspect the relevant sections separately. Raw logs can contain
identifiers; do not upload them publicly.

## Test A: backlight only, awake SoC

Start with a visible, responsive Android session. Capture brightness, bl_power,
DC/display state, battery current and kernel logs. From the existing diagnostic
console, an operator may manually run:

```sh
/bin/display-backlight-cycle --run-backlight-only
```

This script is never called by boot/report/build. It saves a nonzero brightness,
sets only that brightness to zero, restores it, and repeats ten times with a
restoration trap. It does not blank fb0, request SoC sleep, export/toggle GPIOs,
restart services, change power rails or alter charger settings. The operator
must observe ten completely dark intervals and restored brightness/session.
Keep a recovery plan for a disconnected shell/power interruption, where a
shell trap cannot guarantee restoration. Do not run while Android is also
changing brightness aggressively; record any race rather than assuming success.

If zero does not extinguish illumination, stop before Test B and inspect
LP8550 control/readback and original PD0 gate ownership. Do not guess a GPIO
or disable the shared touch/panel supply.

## Test B: Android blank/unblank, awake SoC

Press the real power button to turn off the screen, then press again to wake
the display. Repeat at least ten times, including rapid pairs to detect stale
delayed-disable races. Confirm:

- no visible backlight while off;
- logs show effective zero before DC disabled;
- resume completes scanout before light-on and restores the prior brightness;
- same Android session, no SurfaceFlinger or framework restart;
- GPU rendering, touch/multitouch, Wi-Fi Internet and BT pairing still work;
- DS2781 and charger transitions still update; CPCAP transport identity remains
  0012 and no new interrupt failure beyond the known existing CPCAP issue.

This profile deliberately leaves touch powered/scanning and the shared panel
rail retained; it is not yet a touch or system suspend test.

## Tests C–G: gated, not available in candidate 80

Do not write `mem` or enable automatic suspend in this image. First complete
the hardware-wake and platform/device gates listed in the audit. Later tests
must show entry into the selected LP mode, physical wake, resumed timers/CPU1,
L2, graphics, input, storage, Wi-Fi, Bluetooth and battery readings.

Then perform controlled kernel suspend, Android automatic suspend with active
wakelocks honoured, twenty repeated cycles, and gradually longer periods.
A USB command or userspace timer cannot be the sole wake/recovery mechanism.
Do not proceed to overnight sleep until short and repeated cycles are sound.

## Power comparison procedure

With charger disconnected and comparable radio workload/brightness/temperature,
record repeated DS2781 current readings for (1) display-on idle and (2)
display-off but awake. Compare stable samples, not an animation transient.
For later verified suspend, use valid before/after charge measurements and
elapsed wall time, or external measurement. The gauge cannot be polled by a
sleeping CPU. `/proc/uptime` first column is elapsed time; its second column
is accumulated idle time and is not suspend duration. Do not fabricate a
suspended current value or claim a numerical saving before measurements.

## Rollback

If any new display failure occurs, do not enable deeper power states. Use the
established physical-button fastboot entry and explicitly authorized boot-only
restoration with the preserved working 79 or original boot image. Never write
recovery or repartition. Restore normal Android USB and verify the full boot /
recovery hashes as in previous tests. No rollback command is run automatically
by this work.

## Prepared build identity

Image size: 4145152 bytes. SHA-256: `3847ee00eacbfd66177355c2f46ecdd606dc91705483882f7f167e09a93dc2ca`.
Kernel source head: `3be7bf77`. Hardware state: **not flashed / unvalidated**.

The first build exposed a definite KitKat lights-ABI bug: the adapter returned
ENOSYS for the seven non-backlight light IDs, but KitKat's native
`setLight_native` calls every slot without a NULL check. That could crash
system_server on battery/notification updates. The adapter now opens all eight
IDs; only backlight touches hardware, the rest are safe no-ops. Unknown IDs
still return ENOSYS. The image above is rebuilt with that correction.
