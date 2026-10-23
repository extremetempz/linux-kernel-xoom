# Image 37 — initial two-core Android boot confirmed

24 October 2026. Two independently requested, integrity-checked USB reports
confirm Android 4.4.4 boot completion with both Tegra 2 CPUs online under Linux
4.4.147. The operator also reported that the device booted. The original boot
image has since been restored; both original partitions are verified and the
working original Android ROM remains running.

Kernel: `b6483deb`, profile `android44-smptrace`, `maxcpus=2`.
Image SHA-256:
`b2a3d0ef172c4e1692701b6fa5aee70de36d44bedb1c5888a6b4adda3ed9aa59`.
The [diagnostic implementation and limits](smp-startup-trace-37.md) apply.

## Verified hardware results

- Kernel log reports two processors activated. Both possible/present and online
  masks are `0-1`; the offline mask is empty.
- Both Android boot-completion properties are 1 in both fresh reports.
- The private-memory/affinity probe passes on two CPUs: 64 iterations, 16 KiB,
  exit 0. The Android ABI gate, including expanded ashmem checks, exits 0.
- Both CPUs' local timer (`twd`) counters advance from 8105 to 12099 between
  report snapshots. Reschedule IPIs advance from 5379/10524 to 17319/22382 on
  CPU0/CPU1. Interrupt error count is 0 in those snapshots. These are observed
  activity, not complete interrupt-routing or stress coverage.
- PL310 reports enabled, eight ways, 1024 KiB; CACHE_ID `0x410000c4`,
  AUX_CTRL `0x7e480001`.
- USB reports remain responsive, full eMMC capacity matches, and all ten
  BigPart extents match the original-kernel reference. The read-only storage
  and RAM-data/software-graphics policies remain in effect.

After restoring the original and verifying its images, one bounded read-only
mmap snapshot retrieves the matching SMP trace. It records CPU1 entering the
IRAM reset handler, reaching secondary C after the MM switch and signalling
online completion. CPU0 records a successful startup result (0) and CPU1 online.
The captured reset vector is `0x40000000`; secondary startup is `0x000096a0`.
The reader's temporary deployment was cleaned up; original Android remains
boot-complete with unchanged boot ID and no new fault reported by its log check.

## Preservation and limits

Restoration was acknowledged by fastboot. Complete on-device SHA-256 hashes of
boot (8 MiB) and recovery (12 MiB) match the pinned original images, with exact
partition lengths and a known-answer hash check. Recovery and layout were not
written. No restoration is pending. Raw reports, identifiers and images remain
private and excluded from Git.

This is an initial SMP/PL310 hardware smoke-test success. It is not evidence
that instrumentation fixed image 36: trace writes, barriers and instruction
layout change timing, and the cause of that earlier logo-only result remains
unknown. Repeatability without tracing is still required. There was no long
concurrent stress, broad cache-capacity/memory-pressure test, hotplug, suspend,
DVFS or GPU test. The operator did not explicitly reconfirm touch alignment or
multitouch for this particular boot; retain the earlier tested touch control.

## Next gates

Keep this successful image and its configuration immutable. Re-test the
unchanged non-trace two-CPU image in a separate attempt before attributing the
result to a software correction. If its failure repeats while this control
continues to pass, narrow the timing/layout difference with separate patches;
do not add speculative resets, voltage transitions or Samsung power tables.
Then extend concurrent RAM and per-CPU workload coverage before combining SMP
with DVFS or accelerated graphics. The existing Motorola HWC0/gralloc/EGL and
legacy nvhost/nvmap reuse plan remains a separate integration track.
