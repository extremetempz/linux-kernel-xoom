# Component status — 24 October 2026

**Latest GPU attempt:** [test 48](docs/gpu-render-test-48-result.md) used a RAM-only
NVIDIA offscreen diagnostic with checked reset, fixed low engine clocks and
software-only EMC votes. Build/fault/image checks passed, but hardware produced
no diagnostic USB report; its stopping point is unknown. The original ROM is
restored and both complete original partition hashes match. Linux 4.4 rendering
and accelerated Android composition remain unproven.

**Hardware-tested baseline:** Linux 4.4.147 boots the existing Android 4.4.4
userspace. Image 32 displayed Welcome with working touch; image 33 confirms
Android completion, real single/two-contact events, USB, full eMMC capacity and
all ten BigPart extents without the earlier startup IRQ burst. Original boot
and recovery were restored and completely verified. A lockscreen has not been
verified. This is an experimental RAM-data/software-graphics boot, not a complete
ROM or a newer Android release. Images 37/38 additionally confirm initial
two-core Android boots with PL310, with and without diagnostic tracing.

| Component | What is done | What is not done | Verdict |
|---|---|---|---|
| Tegra 2 SMP / CPU bring-up | Images 37 (traced) and 38 (unchanged non-trace image 36) boot Android with both CPUs online; CPU probes and timer/reschedule-IPI progress pass | Earlier attempt-36 failure remains unexplained; broader repeatability, concurrent stress, hotplug and suspend unvalidated | Initial traced and non-traced two-core boots passed; not fully validated |
| PL310 L2 | Images 34/35/37/38 boot Android with PL310 enabled, 1 MiB; CPU0 and bounded cross-CPU memory checks pass | Broader cache-capacity, RAM-pressure and endurance validation pending | Initial UP/SMP smoke tests passed; not fully validated |
| CPU frequency / voltage | Clock acquisition/unwind, shared EMC failure/rollback reporting, PLL error propagation, voltage-unit correction and stock Wingray table cap implemented; fault tests and ARM object checks pass | Motorola OPP/rail coupling, installed-DRAM EMC tables, voltage-failure veto and complete transition sequencing unvalidated; scaling/voltage driver remain disabled in tested profiles | Prerequisites implemented; not operational |
| NVIDIA nvhost / nvmap | ARM32/submission corrections and reservation checks implemented; separate Motorola carveout-only DT/config builds with matched live-original 256 MiB heap, no IRAM/GART/engines, EMC shims or DVFS; full legacy graphics links also pass; patches 0081–0084 reject clock/IRQ/probe failures and unwind partial setup, with fault tests and full ARM links; attempt 39 boots the isolated profile and passes four 64 KiB uncached create/allocate/pin/map/pattern/cache-ioctl/unmap/unpin/free cycles, with two fresh reports and verified original-image restoration; attempt 40 additionally passes cacheable two-client pattern exchange and imported mapping survival after owner release | DMA coherency, cross-process/concurrent sharing, lifetime stress, host/GART/DC ownership and GPU submissions pending; tested Android profiles retain software graphics | Initial uncached and cached two-client sharing hardware smoke passed; GPU not working |
| EGL / gralloc / HWC | Software graphics reaches Android Welcome; composer bounds/descriptor cleanup corrected; original framebuffer ABI restored with optional synchronous linear-RGB handlers, bounds/completion/lifetime tests and ARM on/off links; offscreen probe passes 13 host cases and now runs two correct NVIDIA Tegra ES2 frames on the original 2.6.39 ROM | Tiled/YUV/scaled posting unsupported; matched accelerated Android image/HAL integration, actual posting/completion/concurrency and accelerated composition pending; probe not yet run on the new Linux 4.4 graphics stack | Initial RGB compatibility implemented offline; accelerated integration incomplete |
| Android 4.4 Binder / ashmem / logger / VM | Real framework startup, Binder protocol 7 check, logger v1/v2 round trips, private-page ashmem test and existing VM/LMK startup demonstrated physically; expanded pin/protection probe passes physically in images 34/35/37/38 | Full Binder transaction/FD, reclaim/OOM and endurance coverage pending; wallpaper RenderScript crashes and Play services ANRs unresolved | Basic KitKat support demonstrated; not fully validated |

Do not count the six headings as six completed hardware features. The strongest
validated milestone is Android 4.4.4 startup with display, touch, USB and storage.
Non-trace SMP repeatability, broader L2 validation, DVFS and legacy GPU enablement remain separate gated experiments.

## Source and evidence

- [Image 33 physical results](docs/trace-boot-attempt-33.md)
- [Image 34 PL310 results](docs/trace-boot-attempt-34.md)
- [Image 35 SMP control results](docs/trace-boot-attempt-35.md)
- [Image 36 two-CPU observation](docs/trace-boot-attempt-36.md)
- [Image 37 two-core Android hardware results](docs/trace-boot-attempt-37.md)
- [Attempt 38 unchanged non-trace two-core boot](docs/trace-boot-attempt-38.md)
- [Image 37 startup trace and validation limits](docs/smp-startup-trace-37.md)
- [PL310/SMP implementation and build controls](docs/decatf-implementation-progress.md)
- [Power, graphics and Android ABI corrections and next gates](docs/power-graphics-abi-stage.md)
- [Decatf graphics full-link corrections, framebuffer gap and rendering test](docs/decatf-graphics-integration.md)
- [Motorola resource validation and initial RGB framebuffer compatibility](docs/graphics-compatibility-42.md)
- [GPU probe on original ROM, clock correction and remaining Linux 4.4 blockers](docs/gpu-rendering-preparation-41.md)
- [Attempt 40 cached sharing and owner-release hardware results](docs/nvmap-cached-sharing-hardware-test.md)
- [Attempt 39 physical allocator smoke test and limitations](docs/nvmap-allocator-hardware-test.md)
- [Built Motorola carveout-only resource profile and original live heap observations](docs/wingray-legacy-resource-profile.md)
- [Decatf reuse classifications and staged plan](docs/decatf-reuse-plan.md)

Kernel corrections are separate exported commits through patch 0094; Android
wrapper changes are separate patches under `android/patches`. Sources, tests
and sanitized findings are committed; proprietary libraries, original device
images, identifiers and raw hardware reports are excluded. Tested configurations
and boot artifacts are preserved. No Samsung board power or display tables were
imported by these stages.

The next work order keeps the six areas above ahead of Wi-Fi, Bluetooth and
charging. [Channel-publication correction and remaining gates](docs/graphics-channel-publication-43.md)
records patch 0085, its fault tests and ARM link, and the runtime
clock/EMC/submission gaps. Linux 4.4 acceleration remains unproven; no new flash.

[Runtime/submission integration](docs/graphics-runtime-integration-44.md) adds
checked parent, EMC, clock and IRQ activation to the main submission path and
related entry points. Patches 0086/0087 pass fault fixtures and the full ARM link.
Motorola resource/provider validation and Linux 4.4 GPU rendering remain
unproven; no device access or flash occurred in this stage.

[Host-only diagnostic image prepared](docs/host-test-image-45-prepared.md):
a separate boot image now packages the checked host clock/IRQ cycle test,
original allocator layout and USB RAM reporter. Offline gates pass; it has
not been flashed and performs no GPU rendering or Android startup.

[Initial host-only hardware test passed](docs/host-test-image-45-result.md):
one physical boot completed three checked host activation/suspend cycles at
the retained 150 MHz rate, with two fresh USB/storage reports and a final zero
host reference count. The original boot was restored and both complete original
partition hashes verified. This does not establish GPU submission/rendering or
completion interrupt delivery; an inherited fsync permission warning remains.

[GPU submission/semaphore checkpoint](docs/gpu-submission-semaphore-46.md):
the isolated original-ROM EGL trace confirms 24-byte headers and use of both
GR2D/GR3D. Decatf semaphore reuse without RPC/AVP and engine-host deferral are
separate patches 0091/0092; fixtures and the full ARM link pass. No new flash or
Linux 4.4 GPU rendering result. Work stopped at the requested usage checkpoint.

[GPU client lifetime checkpoint](docs/gpu-client-lifetime-47.md): patches
0093/0094 reject failed GR3D context-save pins, release partial handlers and
publish engine channels after module initialization. Actual-function fault
fixtures and a fresh full ARM graphics link pass with the prior compile config
unchanged. Checked pre-publication reset and Motorola EMC integration remain;
no new boot image, flash or Linux 4.4 GPU rendering result.
