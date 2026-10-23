# Motorola nvmap allocator test — attempt 39

The isolated resource profile is built from kernel commit bc56d535 and patches
0079–0080. It retains the tested two-core/PL310/USB/MMC/touch wiring, enables
only the legacy nvmap generic carveout and keeps host1x, GPU engines, display
controllers, GART, IRAM heaps, DVFS and Android startup disabled. The screen may
remain at the firmware logo. This is deliberately separate from the tested
Android software-display profile.

The sole heap is 0x30000000–0x3fffffff, contained in the original no-map video
reservation. The original working kernel reports that same 256 MiB generic heap.
Probe registration verifies that every carveout page is excluded from normal
RAM before enabling the allocator.

`diagnostic/nvmap-allocator-probe.c` uses Decatf's ioctl header directly. It
requires the exact resource-profile release, opens only `/dev/nvmap`, and runs
four sequential 64 KiB cycles: create, generic-only uncached allocation, size and
heap queries, pin, physical-address bounds/alignment and base query, shared
mapping, two data patterns with writeback/invalidate ioctl, readback, unmap,
unpin and free. Partial failures unwind acquired resources and return failure.
A separate child runs once with a 30-second kill timeout; the USB reporter
remains independent and returns partial progress if the probe blocks.

The uncached smoke test does **not** prove cacheable-buffer coherency, aliasing,
DMA visibility, cross-client sharing, memory pressure, GPU submission, fences,
EGL, gralloc or hardware composition. Those require separate tests after this
gate. No proprietary graphics libraries are needed for this stage.

## Checks before flashing

- ARM32 static, non-NEON build; Decatf structure widths checked at compilation.
- Host fixture exercises 21 success/failure paths, including wrong release,
  invalid physical ranges, mapping/cache failures and cleanup. These are control
  flow tests, not hardware evidence.
- Verify the compiled isolated resource configuration and DT using
  `scripts/verify-legacy-resources.py`.
- Verify packed kernel identity, ramdisk contents, executable hashes, header
  addresses and boot-partition size. Runtime filesystems are RAM/virtual only.
- Fresh original-ROM identity, battery >=40% or wall power, full original boot
  and recovery hashes, and all ten live BigPart extents must match backups.

Only the boot partition is used for the authorized trial. Collect two fresh,
nonce-bound reports with heap metadata, progress and pass/fail status, then
restore the original boot image and verify both original partition hashes.
A timeout, logo or absent USB is not a verdict about the allocator without logs.

## Results

24 October 2026: **initial uncached allocator smoke test passed on MZ604 P3**.

The boot image SHA-256 is
`f6e59a60e234f329900621acbc2d8f6b5233ef053aa768b2d886441252652ea5`;
its kernel component is
`01b6d6acbde6938597124568f2386d3c4774238e4838f7cb8114434a7d229e7d`.
The actual probe SHA-256 is
`bdf885542cffd3c2b6a67ebbdd1ea580b48aec2a472d5121b008e4baa0edede2`.
The runtime reports `4.4.147-wingray-legacy-resources`, two CPUs brought up,
and successful registration of `generic-0 (262144KiB)`.

Two independently nonce-bound/checksummed USB reports, captured at approximately
72 and 88 seconds uptime, contain all four pattern/cache-ioctl success markers,
`XOOM_NVMAP_ALLOCATOR_PASSED cycles=4 bytes=65536 uncached=1`, and exit status 0.
They observe **one** four-cycle test, not two independent executions or boots.
Both reports confirm full eMMC capacity and all ten original BigPart extents.
Normal RAM ends at 0x2e7fffff; the generic heap remains outside normal RAM.
No kernel panic or Oops appears in either report. The user saw the Motorola
logo, as expected with display takeover and Android disabled.

The optional heap sysfs glob did not produce heap attributes on this profile;
heap size evidence comes from driver registration and allocation size/heap/base
queries in the probe, rather than a new sysfs total-size measurement. The log
also includes an early `fsync_enabled` invalid-permissions warning and a GPIO
registration error; this allocator result does not establish their cause or
resolve them. Driver initialization continued and the bounded test completed.

The original boot image was restored successfully. Both complete partition
hashes match the preserved originals after restoration, with the original ROM
boot complete and a stable boot ID. Recovery was not written. Raw reports and
device identifiers remain private, outside Git.

Next gates: instrument cacheable mappings and safe cache maintenance, two-client
sharing, simultaneous allocations/alias checks and lifetime/release accounting.
Only after those pass should host1x/GART and engine ownership be enabled in
separate profiles. This result does not enable accelerated Android graphics.
