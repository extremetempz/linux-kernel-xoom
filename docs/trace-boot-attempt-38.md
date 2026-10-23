# Attempt 38 — unchanged non-trace two-core Android boot

24 October 2026. The exact image from attempt 36 successfully boots Android
4.4.4 with both Tegra 2 CPUs online on this retry. No kernel rebuild, source
correction or tracing was added to that binary. This shows that tracing is
not required for a successful two-core boot; it does not explain the earlier
logo-only failure or establish reliable startup across repeated cycles.

Image SHA-256:
`d2d2aba301235e948e0e11ed4957764e25d31dfc7bc59a14b643cff8e250cb95`.
Kernel source `395c42f3`, profile `android44-smp2`, `maxcpus=2`.
Both the UP tracer and separate SMP tracer are absent from the tested image.

## Verified observations

Two fresh nonce-bound, integrity-checked USB reports confirm:

- Online CPU mask `0-1`, with no offline CPU; kernel reports two processors.
- Both Android boot-completion flags are 1.
- The two-CPU affinity/private-memory probe passes 64 iterations over 16 KiB,
  exit 0. The expanded Android ABI gate exits 0.
- PL310 is enabled with eight ways and 1024 KiB.
- Both local timer counters advance: 15908/15908 to 18224/18224 at the first
  interrupt snapshot of each report. Rescheduling IPIs advance from
  23286/29962 to 23714/30415. These observations are not complete IRQ coverage.
- Full eMMC capacity and all ten BigPart extents match the original reference.
  Read-only eMMC, read-only system and RAM-data/software-graphics policies hold.

The second report completed after more than three minutes of observation.
Screen content, edge alignment and multitouch were not explicitly reconfirmed
by the operator for this attempt. Their earlier tested configuration is retained.
No concurrent stress, broad cache-capacity test, memory-pressure/OOM test,
hotplug, suspend, DVFS or accelerated graphics test was performed.

## Restoration and evidence boundaries

Fastboot acknowledged restoring the original boot image and rebooting. The
working original Android ROM returned. Complete live boot (8 MiB) and recovery
(12 MiB) SHA-256 hashes match the preserved original files, with exact partition
lengths, known-answer hash control, unchanged boot ID and boot completion.
Recovery and layout were not written. No restoration is pending.

No reserved-RAM trace was retrieved or interpreted: this image has no writer,
and a retained image-37 record would not be evidence for attempt 38. Raw USB
reports, original images and device identifiers remain private.

## Interpretation and next gates

Retain this successful non-trace image and image 37 as immutable controls.
The original failure may be intermittent, but its cause remains unknown.
Do not claim a reset/cache fix from this retry. Further independent boot cycles
and bounded concurrent two-core RAM workloads are needed before calling SMP
stable. Preserve fixed clocks/rails while expanding validation, and keep
Motorola DVFS/EMC and legacy graphics integration as separate changes.
