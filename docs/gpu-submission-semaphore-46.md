# NVIDIA submission trace and semaphore reuse checkpoint

24 October 2026. No flash or reboot in this stage. Original Android remains
running. The preceding host-only hardware pass was committed as `a1f9693`.

## Verified original-ROM rendering and submission format

The existing bounded EGL test was executed under the installed strace 4.6,
tracing only its disposable child. Its environment was applied with strace's
`-E` option, so the probe was not preloaded into the tracer or a system service.
Only temporary files under `/dev` tmpfs were created. Trace size was bounded;
all temporary files were removed. Both runs retained the original boot ID and
Android boot completion. NVIDIA Tegra ES2 identification and both distinct
shader-frame/readback checks passed on the original 2.6.39 kernel.

The second trace records numeric ioctl requests: the tracer's symbolic names
otherwise collide with HID ioctl names and are misleading for NVIDIA devices.
A stateful analyzer tracks device descriptors, header/payload boundaries and
successful flushes. It confirms **24-byte six-word legacy write headers**, with
three GR2D submissions and five GR3D submissions in this probe. Thus the existing
optional Wingray decoder is the format to select for this installed library set.
Both engines are used; a GR3D-only profile would not reproduce this observed path.
The analyzer does not publish command handles, addresses or GPU payload bytes.

The trace also observes successful opens of `/dev/nvmap`, `/dev/nvhost-ctrl` and
`/dev/tegra_sema`. Opening semaphores is observed; this alone does not establish
that missing semaphores would always prevent rendering. No semaphore ioctl was
counted by this trace. This is original-kernel evidence, not Linux 4.4 acceleration.
Raw traces, library material and device identity remain in private artifacts.
The second raw trace SHA-256 is
`cdd7ab77abfe739b6425eaa1eb7644ec8f019579fbc65ef90734b49854968875`.

## Separate reusable kernel changes

Patch 0091, kernel `c574707c`, adds an opt-in `TEGRA_SEMA_STANDALONE` selection
for Decatf's existing `trpc_sema.c`. It compiles and initializes that same
implementation without RPC, AVP firmware, media-server or IRAM use. It is
mutually exclusive with `TEGRA_RPC`; the original RPC build and explicit semaphore
initialization path remain unchanged. Semaphore operations were reused, not
rewritten. No hardware tables, regulators, pinmux or display timings were imported.

Patch 0092, kernel `d7f39737`, defers engine channel setup when the host, allocator
or host class is not ready, before channel allocation can dereference them.
It does not claim to fix the later engine probe/publication cleanup path.

Actual-function fixtures pass for semaphore allocation failure, count consumption,
timeout/interruption, registration failure and duplicate initialization. Another
fixture confirms host/allocator/class deferral performs no channel access.
The synthetic trace tests reject malformed/partial streams, ambiguous ioctl
names and unrelated descriptors, and distinguish a 24-byte payload from a header.
These are provider fixtures, not semaphore concurrency or hardware tests.

The standalone option passes a full ARM vmlinux link in a separate offline
variant of the host-test configuration. Required semaphore and checked-runtime
symbols are linked, without RPC/AVP/DVFS symbols. Changed source files match the
build mirror. Evidence is preserved under `artifacts/semaphore46`; **no boot
image was packaged or flashed**. Previously tested artifact/config directories
remain unchanged. This new semaphore variant has not run on hardware.

## Remaining work

The verified six-word submission format and independently reusable semaphore
interface remove two uncertainties. They do not finish Motorola GR2D/GR3D
clock/reset/EMC integration, late engine initialization/unwind, GART/DMA ownership,
GPU completion interrupts or accelerated posting/composition. The original
EGL probe is ready to reuse once a defensible engine profile exists. Linux 4.4
GPU rendering remains unproven. Work stops at this checkpoint at the user's
request to conserve remaining usage; no hardware cycle is pending.
