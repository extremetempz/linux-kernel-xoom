# Component status — 23 October 2026

**Hardware-tested baseline:** Linux 4.4.147 boots the existing Android 4.4.4
userspace. Image 32 displayed Welcome with working touch; image 33 confirms
Android completion, real single/two-contact events, USB, full eMMC capacity and
all ten BigPart extents without the earlier startup IRQ burst. Original boot
and recovery were restored and completely verified. A lockscreen has not been
verified. This is an experimental RAM-data/software-graphics boot, not a complete
ROM or a newer Android release.

| Component | What is done | What is not done | Verdict |
|---|---|---|---|
| Tegra 2 SMP / CPU bring-up | Existing donor SoC implementation retained; separate two-possible-CPU control kernel fully builds with `maxcpus=1` and unsafe UP tracer disabled | No physical control-profile test or CPU1/IPI/cross-core validation | Build-ready experiment; not hardware complete |
| PL310 L2 | Existing driver and latency settings reviewed; separate UP/L2 kernel fully builds | Runtime packaging/instrumentation and physical cache/RAM-integrity checks pending | Build-ready experiment; not hardware complete |
| CPU frequency / voltage | Clock acquisition/unwind, shared EMC failure/rollback reporting, PLL error propagation, voltage-unit correction and stock Wingray table cap implemented; fault tests and ARM object checks pass | Motorola OPP/rail coupling, installed-DRAM EMC tables, voltage-failure veto and complete transition sequencing unvalidated; scaling/voltage driver remain disabled in tested profiles | Prerequisites implemented; not operational |
| NVIDIA nvhost / nvmap | ARM32 layouts measured; stale nvhost job pointer fixed; optional Motorola 24-byte submission decoder implemented and tested in both formats | No physical nvmap lifetime/cache/GART/engine validation or GPU submissions; alternate legacy drivers remain disabled | Interface work in progress; GPU not working |
| EGL / gralloc / HWC | Software graphics reaches Android Welcome; existing Wingray composer allocation bounds and acquire-descriptor error cleanup corrected and host-tested | Matched accelerated blob/HAL build, asynchronous buffer-fence ordering and actual accelerated composition pending | Software path demonstrated; accelerated integration incomplete |
| Android 4.4 Binder / ashmem / logger / VM | Real framework startup, Binder protocol 7 check, logger v1/v2 round trips, private-page ashmem test and existing VM/LMK startup demonstrated physically; expanded pin/protection probe builds and passes host fault scenarios | Expanded probe not yet run on hardware; full Binder transaction/FD, reclaim/OOM and endurance coverage pending; wallpaper RenderScript crashes and Play services ANRs unresolved | Basic KitKat support demonstrated; not fully validated |

Do not count the six headings as six completed hardware features. The strongest
validated milestone is Android 4.4.4 startup with display, touch, USB and storage.
CPU1, L2, DVFS and legacy GPU enablement remain separate gated experiments.

## Source and evidence

- [Image 33 physical results](docs/trace-boot-attempt-33.md)
- [PL310/SMP implementation and build controls](docs/decatf-implementation-progress.md)
- [Power, graphics and Android ABI corrections and next gates](docs/power-graphics-abi-stage.md)
- [Decatf reuse classifications and staged plan](docs/decatf-reuse-plan.md)

Kernel corrections are separate exported commits through patch 0068; Android
wrapper changes are separate patches under `android/patches`. Sources, tests
and sanitized findings are committed; proprietary libraries, original device
images, identifiers and raw hardware reports are excluded. Tested configurations
and boot artifacts are preserved. No Samsung board power or display tables were
imported by these stages.
