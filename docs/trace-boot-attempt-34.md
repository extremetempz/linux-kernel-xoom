# Image 34 — first PL310 hardware control

23 October 2026. A fresh nonce-bound USB report confirms Android 4.4.4 boot
completion with the PL310 driver enabled on the UP control. The expanded
private ashmem ABI probe and CPU0 private-memory check pass. Full eMMC capacity
and all ten BigPart extents match the working-kernel reference.

Image SHA256: `2c70f714c38c15849be3561b594544af962d888fc08faac193ff2eff91abf5f6`.
Kernel: existing candidate-34 build, source `3a12d776`, profile `android44-l2`.
SMP, frequency scaling, suspend and legacy NVIDIA graphics remain disabled.
The tested display/touch wiring and read-only/RAM-data policy are retained.

The captured kernel log reports:

- PL310 enabled, eight ways, 1024 kB.
- CACHE_ID `0x410000c4`, final AUX_CTRL `0x7e480001`.
- Errata 727915 and 769419 enabled.
- ID prefetch enabled with one-line offset.

Both Android boot-completion flags are 1. The native ABI gate exits 0, including
new ashmem pin/protection checks. The CPU probe reports one CPU, 64 iterations
and a 16 KiB private-memory comparison with exit 0. This is a bounded smoke
check, not an exhaustive L2 capacity, memory-pressure or endurance test.
Touch driver metadata is collected, but the operator has not explicitly
confirmed screen content or touch behavior for this boot.

Original boot was restored. The first ADB readback attempt returned one short
chunk and was not accepted as verification. A separate complete retry with
128 KiB transfers matches both original images exactly, with the same boot ID
throughout and original Android running. No restoration is pending. The cause
of the short transfer was not established. Recovery and layout were not written.
Raw reports and identifiers remain excluded from Git.
