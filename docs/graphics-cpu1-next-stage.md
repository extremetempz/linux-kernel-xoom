# Original KitKat graphics path and CPU1 test sequence

23 October 2026. User requested accelerated graphics/synchronization followed
by enabling CPU1 and flashing. These remain independent test tracks; the CPU
control images deliberately keep the tested software graphics path.

## New direct baseline evidence

A bounded read-only `dumpsys SurfaceFlinger` capture from the restored original
ROM reports NVIDIA OpenGL ES 2.0, hardware composer present/enabled, and
`Hardware Composer state (version 0)`. The initial accelerated Android 4.4
integration should therefore reuse the original Motorola HWC0/gralloc/EGL set
with its matching legacy kernel interfaces. A later HWC1 wrapper migration is
not a prerequisite for this installed KitKat stack. This does not establish
that those blobs work with the current Linux 4.4 kernel.

The existing legacy nvhost/engine/nvmap subsystem compiles as ARM relocatable
objects after the earlier separate fixes. Legacy display/resource ownership,
GART/carveout validation, the RAM-only NVIDIA overlay, rendering and syncpoint
behavior are still pending. No legacy graphics driver was enabled or flashed.
Do not describe acceleration as complete.

The original Motorola source reserves 256 MiB of carveout, 8 MiB fb0 and
16 MiB fb1. The live original resource map confirms fb0 at `0x2e800000`
and fb1 at `0x2f000000`. These are Motorola references, not permission to copy
Samsung memory, panel timing or regulator tables. IRAM allocations must also
preserve the Tegra CPU reset-handler region before graphics and SMP are combined.

## Prepared CPU experiments

1. Image 34: UP + PL310, physical boot result recorded separately.
2. Image 35: SMP kernel, `maxcpus=1`, exact same board wiring and fixed clocks.
3. Image 36: separate `android44-smp2` kernel, `maxcpus=2`, no hotplug or UP-only
   RAM tracer. The full ARM link and compiled DT/config negative controls pass.

Image 35 subsequently passed its physical one-CPU SMP control; see its
[report](trace-boot-attempt-35.md). Image 36 was flashed but stayed at the
Motorola logo without diagnostic USB during two minutes; see its
[observations and limits](trace-boot-attempt-36.md). CPU1 operation is not proven. Each experiment requires its preceding control, original-image
readback, boot-only test, USB report and original restoration. The two-CPU
configuration is a new exported source patch 0069; tested control configs are
unchanged.

Exact-release runtime gates now cover these explicit profiles. A static probe
pins only its own process, confirms CPU identity using `getcpu`, and checks a
private 16 KiB buffer over 64 affinity steps. It changes no global CPU setting,
opens no hardware and performs no persistent write. For image 36 it must run on
both CPUs; failure blocks Android startup while USB diagnostics remain available.
Host fault scenarios cover every step, rejected affinity, wrong CPU, corrupted
memory and wrong release. This is not a concurrent stress/IPI or endurance test.
The existing software graphics and guarded read-only eMMC/RAM-data policy remain
mandatory in these CPU experiments.
