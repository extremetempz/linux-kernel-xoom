# First Image 93 LP2 attempt — unresolved, not accepted as LP2

1 November 2026. The manual LP2 request returned a zero result and the physical
power button was used to wake the tablet. Android, touch, display and Wi-Fi
were subsequently usable. These are positive observations, but the kernel
evidence does not identify a genuine Tegra LP2 entry.

## Observed

```text
LP2TEST_WRITE_RC 0
LP2TEST_AFTER completed=1 last_result=0 armed=0 lp2_only=1 platform_entry=manual
LP2TEST_RETURNED
LP2TEST_PROCESS_RC 0
```

Current boot: `d788416d-4523-4bd9-b0e7-93b9a0cc292e`.
Retained console: previous boot `e80b3c39-39e2-4503-8a33-e246c5069f1f`.
No pre-test boot ID or baseline report was saved.

The same-boot report contains:

```text
PM: resume of devices complete after 411.619 msecs
PM: Finishing wakeup.
PM: suspend exit 1970-01-01 00:02:48
```

and no:

```text
WG_LP2_PLATFORM_ENTER mode=LP2 online=1
WG_LP2_CPU_RESUMED
PM: suspend entry
tegradc tegradc.0: suspend
```

for this attempt. The retained console is from the previous boot and cannot
establish what happened in this attempt.

## Assessment

`LP2TEST last_result=0` proves only that `pm_suspend(PM_SUSPEND_MEM)` returned
success. It does not prove:

- `tegra_suspend_enter()` was called;
- the CPU complex lost power;
- the physical wake came from LP2 rather than a reboot;
- PL310/TIMERUS/DRAM/CPU context were restored.

The `1970` timestamp is suspicious but the operator reports wall time has
always been wrong on this build, so it is not independent evidence.

The physical power-button wake and working Android session strongly suggest a
low-power transition occurred, but this cannot be accepted as LP2 without the
`WG_LP2_PLATFORM_ENTER`/`WG_LP2_CPU_RESUMED` and a matching boot ID.

## Required before another attempt

1. Save a pre-test REPORT with `CURRENT_BOOT_ID` and uptime.
2. Add `/sys/power/pm_test` and `/sys/power/wingray_lp2_test` to the report.
3. Capture the current-boot PSTORE record, not only the previous boot record.
4. Run one attempt.
5. Capture a post-attempt REPORT and PSTORE without rebooting or flashing.
6. Compare boot IDs and require the two LP2 markers.

Do not retry the current image automatically. Do not claim LP2 success or
failure beyond "unresolved pending instrumentation."
