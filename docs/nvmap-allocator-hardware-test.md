# Motorola nvmap allocator test — prepared, not hardware validated

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

Pending physical deployment. No allocator hardware pass is claimed.
