# Image 91 — full-tree devices-only DPM test profile

1 November 2026. Builds on Images 89/90. **Source/build only; not flashed.**
Hardware sleep, platform entry, CPU1 offlining and syscore remain blocked.

## What Image 91 adds

- A new default-off `MOTOROLA_WINGRAY_DPM_TEST` mode and
  `/sys/power/wingray_dpm_test`.
- A one-shot root request that freezes tasks, then runs the existing Linux
  `dpm_prepare()`/`dpm_suspend()`/`dpm_resume()`/`dpm_complete()` family
  through `suspend_devices_and_enter(PM_SUSPEND_FREEZE)`.
- `pm_test_level` is temporarily set to `TEST_DEVICES`, preserving the
  existing kernel PM test infrastructure. It restores the previous level.
- `platform_suspend_begin`, CPU offline, noirq/low-level entry, syscore and
  Tegra suspend ops are not reached. The build-time Wingray block remains.
- CPCAP callbacks now have two explicit modes: selected test
  (`pm_test_active`) and genuine DPM ordering (`wingray_pm_dpm_test_active`).
  Neither path runs unless the profile/boot compatibility checks pass. The
  ordinary system-suspend block was not removed or weakened.

Image 91 deliberately **does not claim display/GPU restoration**. The legacy
DC system resume path still uses `_tegra_dc_set_default_videomode()` rather
than the hardware-tested framebuffer all-window restoration path. That
mismatch remains a blocker; a full-tree DPM run may fail or leave the display
unrestored. This profile is for observing the first real dependency error, not
for a user sleep feature.

## Built image

`artifacts/dpm91-final-ready/wingray-android44-gpu.img`
Size 4,216,832 bytes.
SHA-256 `934ceaf67c38b2b4a415b5c7020af6bdae9f4b772cf66a9155bbee5885072164`.
Manifest profile `android44-devicepm91`; `soc_suspend_enabled=false`,
`dc_resume_experimental=false`, `hardware_tested=false`.

## Expected command and result

After Image 90 passes and only with explicit boot-flash authorization:

```sh
python3 scripts/run-dpm-test.py \
  --output-dir artifacts/dpm91-cycle1
```

Status before the request:

```text
completed=0 last_result=0 selected=dpm whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked
```

Expected successful payload:

```text
DPMTEST_WRITE_RC 0
DPMTEST_AFTER completed=1 last_result=0 selected=dpm whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked
DPMTEST_COUNTER_ADVANCED_1
DPMTEST_PROCESS_RC 0
```

Kernel markers include `WG_PM91_FREEZER_COMPLETE`, per-driver PM messages, and
`WG_PM91_DPM_COMPLETE result=... platform_entry=0 cpu_sleep=0`.

**USB may disappear while devices are suspended.** Do not depend on frozen
Android userspace. The server saves the fixed result in `/run/dpm-test.txt`;
after re-enumeration the fixed `DPMSTATUS` request can retrieve it without
running another cycle. No automatic retry is implemented.

## LP2 source corrections (not hardware-validated)

- `tegra_suspend_enter()` now rejects NONE/LP0, requires a non-null sleep
  function and exactly one online CPU, propagates `cpu_suspend()` failure,
  restores FIQ/clock/flow state and clears LP2 mask state.
- The LP2 finish path now performs `flush_cache_all(); outer_disable()` before
  MMU-off, covering dirty PL310 lines; CPU1/DMA quiescence remains a hard
  prerequisite.
- Timer SUSEC config is saved/restored through a syscore operation.
- PMC DT parsing initializes all optional fields, requires CPU timers for
  every mode and core timers only for LP1/LP0, and validates LP0 vector only
  for LP0. LP2 no longer needs invented core timing values.

These are source-level corrections. LP2 entry, LP1, LP0, physical wake and
power measurements remain unvalidated.

## CPU1 hotplug preparation

A separate CPU1 test is still required before LP2: use `CONFIG_HOTPLUG_CPU`,
offline CPU1 with `echo 0 > /sys/devices/system/cpu/cpu1/online`, keep CPU0
running, then online it and verify both CPUs schedule, IRQs/timers continue,
and no cache/SCU fault appears. Do not combine it with LP2 or CPU0 offlining.
No automated CPU1 test is enabled in this profile.

## Readiness

| Item | Status |
|---|---|
| Task freezer | Hardware-validated on Image 89 (documented; artifacts absent here) |
| CPCAP selected callbacks | Implemented; hardware test pending |
| Full devices-only DPM | Implemented in Image 91; hardware test pending |
| Display/GPU system restore | **Blocked/unimplemented** |
| Storage/wireless/touch/battery callbacks | Partly implemented; not system-PM tested |
| Wake source | Awake arm/disarm passed; system-PM wake blocked |
| PMC configuration | Parser fixed; board handshake and entry blocked |
| CPU1 hotplug | Implemented; no controlled test |
| PL310 handling | Source fix added; no hardware test |
| Timer handling | Syscore wiring added; no hardware test |
| LP2 entry | Not runnable; platform/wake/device gates remain |
| Physical power-button wake | Not validated |
| ECC/pstore recovery | Limited hardware claim; private artifacts absent here |

## Build

```sh
XOOM_ANDROID_GPU_PROFILE=devicepm91 \
XOOM_BUILD_ROOT=/tmp/xoom-devicepm91-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/devicepm91-new-build" \
XOOM_IMAGE_DIR="$PWD/artifacts/devicepm91-new-ready" \
JOBS=6 bash scripts/build-android-gpu.sh
```

No device operation, flash, reboot, sleep request or CPU offlining is part of
the build.

## Rollback

Keep the Image 89/90 boot image and original boot/recovery backups. On any
hang, power-cycle, enter fastboot, and restore the known-good boot image; do
not repartition or flash recovery. Preserve ECC/pstore before restoring an
older kernel when possible.
