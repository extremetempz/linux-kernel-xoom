# GPU rendering preparation — 24 October 2026

Historical checkpoint: runtime/host validation and context cleanup have since
advanced. See [current GPU client lifetime checkpoint](gpu-client-lifetime-47.md)
for the updated source status and remaining reset/EMC gates.

**No flash or reboot in this stage.** The preceding cached-sharing checkpoint
was already committed and uploaded to private main. SMP/PL310, allocator-only
and Android software-display configurations remain unchanged.

## A real rendering probe now runs on the original ROM

The existing EGL probe was built for ARMv7/VFPv3-D16 without NEON, using the
owner's preserved KitKat EGL/GLES2/libc and matching shared-library startup
objects. Standard EGL/GLES declarations come from installed Khronos headers;
its small optional C/POSIX declaration header avoids importing a host libc or
host `FILE` layout. The normal Android.mk build retains platform headers.
No vendor library is redistributed or replaced.

A gated constructor allows the same probe to run in one disposable dynamic
child on KitKat without a complete Android source build. It requires the exact
`XOOM_EGL_PROBE_CHILD=1` environment value. It is never injected into Android
init or a running service. Five host fixture cases test the explicit gate;
13 existing Mesa/fault cases still test the actual rendering client. These
host tests do not themselves establish hardware rendering.

The physical baseline test used the **working original
2.6.39.4-ElementalX-Xoom-2.1+ kernel**, with installed wrapper and NVIDIA renderer
library hashes matching the preserved files. Only a temporary module under
`/dev` tmpfs was transferred. The fixed runner starts one new child, bounds the
probe with its existing 20-second alarm, captures its status and removes the
RAM module afterward. It does not modify installed graphics settings, Android
services, on-disk libraries, boot or recovery.

Observed output:

```text
egl=1.4 vendor=NVIDIA Corporation renderer=NVIDIA Tegra version=OpenGL ES 2.0
frame=0 triangle_and_background_readback=pass
frame=1 triangle_and_background_readback=pass
XOOM_EGL_OFFSCREEN_READBACK_PASS (not composition/fence validation)
XOOM_EGL_CHILD_STATUS 0
```

Each frame draws a shader-generated triangle and checks foreground/background
pixels, using different colors for the second frame to reject stale output.
The ARM module contains no Mesa identity wrappers. This is actual NVIDIA-stack
render/readback evidence on the **original** kernel, not on Linux 4.4. It also
shows that this blob set can create the bounded pbuffer in its original running
Android environment. It does not establish pbuffer independence from a working
framebuffer/gralloc stack in a new environment.

The module SHA-256 is
`606d7757d6b290599bb3e6c0f7de8f88d35c91d66ac17df591b29582e37abb1d`.
Private artifacts retain the exact module, original library/header hashes and
captured output. The temporary directory was removed, the original boot ID was
unchanged and Android remained boot complete. No new boot image was produced.

## Separate kernel correction: required clock setup

Patch **0081**, kernel commit `225b9f80`, corrects Decatf's existing
`nvhost_module_init` clock acquisition rather than replacing its driver.
Previously a failed `clk_get` was skipped while its slot was counted, and
round-rate, prepare/enable and set-rate results were ignored.

The correction resolves and validates the complete named list before changing
rates, propagates provider errors including probe deferral, rejects null/zero
providers/rates, checks preparation and setting, balances enables/references,
restores previously attempted rates on transaction failure, and reports failed
rollback without hiding the original error. Later sysfs-allocation failures
release the acquired clock references. Such late failures do **not** promise
complete power-domain or clock-rate rollback; the broader power lifecycle is
not validated by this patch.

Twenty-four actual-function host cases cover success, failure at each of three
slots, zero/null providers, failed rollback and zero-clock modules. UBSan runs
on the fixtures. The full ARM legacy-graphics `vmlinux` link passes with the
Motorola RGB compatibility path enabled and modern/Samsung owners excluded.
Artifacts under `graphics-host-clock-41` are a **compile checkpoint**, not a
physical boot attempt or deployable image. Tested config/DT sources are intact.

## Further independent host bring-up corrections

| Patch | Kernel commit | Scope and validation |
|---|---|---|
| 0082 | `f1f1a8f5` | Interrupt init is software-only; explicit start returns syncpoint/general IRQ errors, unwinds a partially registered pair, and guards repeated start/stop. Wait lists exist before activation; worker work drains on deinit. Actual-function host tests cover failed first/second request, duplicate start, idle stop and restart. |
| 0083 | `4e193b89` | Missing nvmap defers binding. The host checks all clock enables before register access, checks an initial IRQ start/stop, and publishes its global/control references after initialization. Failed setup unwinds mapping/region, allocator, clocks, worker and sysfs resources. A dedicated abort path avoids power callbacks on partial state. Actual probe tests cover all 14 failure stages and missing/deferred resources; control-device tests cover four failures. |
| 0084 | `2bb6dda5` | Partial syncpoint sysfs cleanup only removes initialized attributes. Actual init/cleanup tests cover 13 failure stages and repeated cleanup, including child-kobject/reference release. |

The 0083 full ARM link passed with the Motorola RGB compatibility path enabled.
The final 0084 link and artifact identity are recorded in private
`graphics-host-lifetime42` compile evidence. These patches do not implement or
validate Motorola power/EMC sequencing, runtime failure veto through every
submission caller, active-job removal, IRQ races under load or GPU completion.
Fixtures use idle queues and provider stubs; they are not concurrency or
physical-interrupt proofs. No tested defconfig or DT was altered.

## Why Linux 4.4 acceleration is still not ready to flash

The original-ROM render pass validates the test and the installed library set.
It does not close these concrete new-kernel dependencies:

1. The tested resource DT deliberately disables host1x, GR2D/GR3D and DC. Its
   generic allocator cannot expose or execute GPU channels.
2. The previously identified early register-access ordering and probe cleanup
   issues are corrected by 0082–0084 and fault-tested, but not hardware-tested.
   Host reset state, register behavior and real IRQ delivery remain unvalidated.
3. Initial IRQ-request failures are now propagated and balanced. Runtime
   clock-on still uses a void callback: it logs an IRQ-start error but does not
   veto every channel submission caller. Engine/client setup and active-job
   teardown require further review before enabling GR3D. The original source
   issues have not been proven to cause a physical failure on this port.
4. The current Tegra DT nodes have no explicit legacy host/GR3D clock names and
   only one GR3D clock, whereas Decatf requests `gr3d` and `emc`. Named clkdev
   fallback resolution is unvalidated. An explicit Motorola profile must resolve
   those providers, rate/voltage/DRAM safety and reset/power ownership. Do not
   satisfy missing clocks by blindly importing Samsung power or EMC tables.
5. GART/IOVMM, channel submission and syncpoint completion have not been tested
   on this port. The optional Motorola 24-byte submission decoder, existing
   Decatf context/command machinery and original library dialect must agree.
6. The full legacy compile profile is not the tested allocator profile: it
   still enables page pools/compaction and lacks the resource DT. The matched
   legacy framebuffer/HAL path, allocation formats and completion semantics
   must be validated before using it for EGL or composition.

These prevent a defensible claim that flashing the current link artifact can
render on the GPU. Nothing was flashed to guess at those dependencies.

## Next separate patches and checks

- Done offline in 0082–0084: checked-clock probe ordering, deferred nvmap,
  staged error cleanup, late host/control publication, initial IRQ errors,
  wait-list initialization and IRQ/worker start/stop lifetime.
- Next: propagate runtime clock/IRQ errors through channel submission and
  audit engine-client deferred binding/cleanup. Successful bind alone must
  not be treated as rendering readiness.
- Add a separate Motorola host/engine profile after the source/resource audit,
  retaining tested reservations, CPU reset-vector exclusion, AUO timing and
  power controls. Verify compiled DT/config and full ARM links with negative
  controls. Validate GART and fixed clock/reset dependencies independently.
- Use this same hardware-validated probe and matched original libraries for
  the eventual Linux 4.4 offscreen test; require NVIDIA identity and both fresh
  frames. Framebuffer/HWC/fence validation follows that result, not precedes it
  as a claim of acceleration.

Reproduce the offline work:

```sh
python3 tests/test-nvhost-clock-init.py
python3 tests/test-nvhost-irq-start.py
python3 tests/test-nvhost-probe-order.py
python3 tests/test-nvhost-user-lifetime.py
python3 tests/test-nvhost-syncpt-lifetime.py
python3 tests/test-egl-preload-entry.py
python3 tests/test-egl-probe.py
python3 scripts/build-kitkat-egl-probe.py --output-dir artifacts/NEW-egl-module
```

`run-original-egl-probe.py` is an explicit device action restricted to the
original ROM. It is not part of build scripts or any boot startup path. A failed
or timed-out probe is not automatically retried. None of these scripts flashes.
