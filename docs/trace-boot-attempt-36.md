# Image 36 — two-CPU startup not demonstrated

23 October 2026. The separate `android44-smp2` profile allows both CPUs with
`maxcpus=2`, retaining the image-35 control's fixed clocks and PL310 support.
Frequency scaling, voltage changes, hotplug and accelerated graphics remain
disabled. The UP-only persistent tracer is deliberately disabled.

Image SHA256: `d2d2aba301235e948e0e11ed4957764e25d31dfc7bc59a14b643cff8e250cb95`.
Kernel source revision: `395c42f3`.

## Observations

- Preflight matched both complete original images and all ten BigPart extents.
  Battery was 99%; the operator elected to disconnect the wall charger.
- Fastboot acknowledged the boot-only flash and reboot.
- During the two-minute observation the operator reported the Motorola logo.
  The guest did not observe a diagnostic USB device.
- No diagnostic report was retrieved. CPU1 online state, Android completion,
  and the exact stopping point are unknown.
- The first restoration attempt identified the fastboot product but timed out
  during the original-boot flash. USB was subsequently absent from the guest.
  This attempt was not accepted as a completed restoration.
- After the operator reconnected USB, fastboot acknowledged the original-boot
  restoration and reboot. Recovery and partition layout were not written.

Image 35 proves Android can run with this SMP configuration restricted to CPU0.
The contrasting result makes the additional CPU startup/execution path the
priority for investigation. It does not prove a particular reset, SCU, cache,
timer, interrupt or scheduler defect. Nor does absence of USB alone establish
that the kernel stopped before USB initialization.

## Restoration verification

The original Android kernel and boot completion were confirmed. Bulk ADB
readback stalled after one 128 KiB chunk; it was not accepted as complete
verification. After reconnecting the host transport, an alternative read-only
check computed SHA-256 on each complete live partition. Both hashes match the
preserved originals, with exact partition lengths (8 MiB boot, 12 MiB recovery),
a known-answer SHA-256 control, unchanged boot ID and Android still complete.
No restoration is pending. This is full-content hash verification, not a
completed host-side byte-for-byte readback. USB instability also affected the
original ROM; its cause has not been established.

## Next diagnostic gate


Preserve images 34 and 35 as controls. Compare the actual CPU1 reset vector,
IRAM trampoline, reset/clock release sequence, secondary entry, SCU coherency,
and per-CPU interrupt/timer setup against Motorola's working implementation.
Use separately reviewed instrumentation to distinguish CPU0 requesting startup,
CPU1 entering the trampoline, CPU1 reaching C initialization, and CPU0 observing
CPU1 online. The existing UP-only tracer must not simply be enabled under SMP.
Capture the first failure before introducing DVFS or graphics changes.

Raw reports, USB identifiers and original images remain private.

## Subsequent control result

[Image 37](trace-boot-attempt-37.md), with separate startup tracing, subsequently
booted Android with both CPUs online. This establishes that the retained donor
startup implementation can work on this hardware; it does not explain or
retroactively diagnose the image-36 failure. Non-trace repeatability is pending.
