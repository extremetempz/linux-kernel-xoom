# P9-only physical repair passed — 3 November 2026

The operator explicitly armed and confirmed the reviewed p9-only transaction.
The reply-checked client verified the hardware RAM suite, all-ten BigPart layout,
all-RO policy and original source hash first; the on-device wrapper repeated
preflight immediately before release. The standalone checker replayed p9's
journal and requested only the known inode-bitmap padding correction. The
operator accepted that correction.

Results: repair exit 1 (corrected), checked all-partition RO restoration, p9
relocked RO, full five-pass read-only recheck exit 0, and completion marker.
Physical p9 SHA-256 after repair:
`09b94b39fb08e3c1db8d5fa1c63949185b8dc08f99c265047e9f263c184001a1`.
See the [machine-readable receipt](cache99-physical-repair-result.json) for the
private transcript hash. The transcript remains local; no raw cache data is
included in Git. The repaired physical hash differs from the host experiment,
which is expected to be possible because repair timestamps/journal state differ.

Only p9 was released by this gate. The kernel protected p10/system/boot/recovery/
whole-disk writes throughout; no byte-for-byte post-test hashes of those physical
partitions were acquired in this transaction. No format, host-image restore,
cache mount, Android boot or persistent-cache enablement occurred.

The verified dirty original backup remains a separate preserved acquisition.
The current image is still the offline repair image. Next: enter fastboot, flash
only boot with the immutable p9 backup image, acquire a NEW cache evidence bundle
and require both source passes/image hash and healthy source/image checks.
Persistent cache stays blocked until that new evidence passes. Do not reuse the
old dirty bundle, and never replace the old original backup with the repaired
filesystem image.
