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

A second attempt on the same boot (`d788416d…`) advanced the LP2 counter to
2, again returned zero, and the physical power button woke Android. The
post-attempt report shows `PM: resume` and `PM: suspend exit` but still no
`WG_LP2_PLATFORM_ENTER` or `WG_LP2_CPU_RESUMED`. The pre/post uptimes show the
same boot. The pre-test report was taken after the attempt, not before it, so
it did not establish a clean baseline.

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
always been wrong on this build, so it is not independent evidence. The
current report lacks `/sys/power/pm_test`, so an early pm_test skip cannot be
excluded.

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


## Root cause of the missing markers

Later analysis showed the saved dmesg was only the last 262144 bytes and was
entirely a CPCAP IRQ `-108` flood. The retained console stopped at
`PM: suspend entry` because normal Linux console suspend was still enabled.
The original Motorola board set `console_suspend_enabled = 0`; that was missing
from Image 93. Image 93d restores it so the `WG_LP2_*` and teardown lines are
retained for the next attempt.
