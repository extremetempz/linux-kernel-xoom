# Startup trace 49: panic before RAM userspace

24 October 2026. One guarded, stable readback recovered a valid cookie-49 record
after the boot-only test and original-image restoration. Its SHA256 is
`a1f975385a91efba9c776bc7bb10b10e65429d0502e0dce65711f9b613dd8caa`.
The matched `System.map` SHA256 is
`832f29101e118c1ca2948f9fe2be939653bd3dc4abcb5891a671933bf8158b2d`.
Raw data, identifiers and transport logs remain private.

## Verified observations

- CPU0 stage 17, CPU1 reset stage 1, CPU1 C stage 5, startup result 0 and
  online bit 1 record completed initial secondary-CPU bring-up.
- Host stage 61/result 0 records successful host probe publication.
- GR2D and GR3D each record stage 41/result `-22` (`-EINVAL`): their module
  initialization returned failure. The outer return marker overwrote finer
  internal progress, so this record cannot identify its exact failing operation.
- The panic notifier ran. Kernel stage remains 4 (basic setup/late startup,
  before freeing init memory); no first-exec or RAM userspace marker was reached.
- Last recorded PID1 initcall is `clk_disable_unused`, state returned, result 0.
  It is **not** recorded as stuck inside that function.
- USB composite probe recorded stage 2/result 0. Neither reporter/userspace
  stream recorded progress, and the guest saw no diagnostic USB device.

The evidence locates this attempt's panic before the RAM diagnostic could
start, rather than in the two-frame rendering probe: this image never invokes
that probe. It does not establish the panic message, prove that the engine
errors caused the panic, or prove that candidate 48 failed identically. A prior
completed initcall is not evidence that it caused a later panic.

## Preservation and retrieval

The first restoration checks saw no USB handoff and performed no write. After
the operator connected fastboot to the guest, original boot restoration and
reboot succeeded. ADB returned after the requested startup interval. Complete
boot (8 MiB) and recovery (12 MiB) hashes match both original backups; recovery
and layout were not written. No restoration remains pending.

The reader used the existing tested read-only mapping method, once, after fresh
original-kernel/image/memory-map checks. The temporary reader lived in `/dev`
RAM and was removed. Original Android stayed boot-complete with unchanged boot
ID and no newly detected fault in the before/after log comparison.

## Focused follow-up

Retain a short panic-message prefix and per-clock acquisition/rate-validation
failure codes in a new cookie-50 record. Preserve the inner clock rejection
stage when module initialization fails instead of overwriting it with its outer
return marker. Keep rendering disabled and the same DT/rate policy. This will
separate the boot-stopping panic from the independently observed engine errors
before making a functional correction.
