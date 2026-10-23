# Image 35 — SMP kernel with CPU1 deliberately offline

23 October 2026. A fresh integrity-checked USB report confirms Android 4.4.4
boot completion with the SMP kernel restricted by `maxcpus=1`.

Image SHA256: `e4f654a517cfa76067ce9027f7c4041147a6f31f40bb2fdb33629cd9be59cfb7`.
Profile: `android44-smp`. Both possible and present CPU masks are `0-1`;
online is `0`, and offline is `1`, as intended for this control.

Verified results:

- Both Android boot-completion flags are 1.
- The Android ABI probe exits 0.
- The CPU0 probe passes 64 iterations over 16 KiB of private memory, exit 0.
- PL310 is enabled, eight ways and 1024 kB.
- Full eMMC capacity and all ten BigPart partitions match the reference.
- After restoration, complete boot and recovery readbacks match their preserved
  originals. Original Android is running; recovery and layout were not written.

This validates the one-CPU SMP control, not CPU1 execution or cross-CPU cache
coherency. The bounded memory probe is not an endurance test. Screen content
and touch alignment were not explicitly confirmed by the operator for this
boot. Frequency scaling, voltage changes and accelerated graphics remain
disabled. CPU1 is the next isolated hardware test.

Raw reports and device identifiers remain private and excluded from Git.
