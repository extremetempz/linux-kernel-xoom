# Retained startup checkpoints, image 49

Prepared 24 October 2026 after [attempt 48](gpu-render-test-48-result.md) produced
no USB report. **No cause of that stop has been established.** This image is a
startup-localization control; its RAM service does not load the EGL probe or
submit userspace GPU jobs. Rendering must remain a later test.

## What changes

Patch 0098 adds a default-off `MOTOROLA_XOOM_GPU_STARTUP_TRACE` option and separate
`wingray_gpu_startup_trace_defconfig`. It selects the already tested SMP trace
implementation with new build cookie `0x584d0049` and uses its existing uncached
mapping. The record remains exactly 128 bytes at physical `0x1fe00000`, inside
the existing reserved/no-map console hole. No new RAM reservation, UART,
regulator, pinmux, display timing, voltage or DRAM timing programming is added.

The compiled DT is byte-identical to candidate 48. Engine clocks, fixed EMC
vote policy, allocator and submission ABI are unchanged. The tested source
profiles and their old artifacts remain preserved. Instrumentation changes
instruction layout/timing and is not a functional fix.

| Record | Writer and meaning |
|---|---|
| Existing SMP fields `0x10–0x28` | Original CPU0, CPU1-reset and CPU1-C streams; initial IO mapping through CPU1 online result |
| Initcall `0x2c/0x30/0x34` | PID1's function address, signed result, and state: 0 updating/unknown, 1 entering, 2 returned |
| Host `0x38/0x3c` | Host probe/module/clock/publication stage and signed result |
| GR2D `0x40/0x44`; GR3D `0x48/0x4c` | Independent per-device probe, context, module, reset and publication stage/result |
| Kernel `0x50/0x54` | Kernel-init, SMP, basic setup, freeing init memory and first userspace exec progress/result |
| Reporter `0x58` | 1 loop started; 2 serial node seen/server entered; 3 valid framed request accepted |
| Userspace `0x5c` | 1 bootstrap mounted `/dev`; 2 before original Android init; 3 startup service entered; 4 all GPU nodes present; 5 timeout/missing nodes |
| USB `0x60/0x64` | Serial composite probe/bind stage and signed result; this is not proof the host enumerated it |
| Panic `0x68` | 1 means the panic notifier ran; it does not identify the panic's cause |

Engine stage codes: 10 client/probe entry, 11 host deferral; 20 channel
allocation; 30/31 context initialization enter/return; 40/41 module enter/return.
Inside module setup, 41/42 are clock setup, 43/44 power setup and 45 attribute
creation. Reset setup uses 50/51 entry, 51/52 checked activation, 53/54 reset
assertion, 55/56 deassertion, 57/58 clock-gating exit. 60/61 mark publication
entry/return. Nested operations overwrite the outer stage while in progress.
For host probe, 50 is initial clock activation, 60 publication, 61 success and
255 failure return. Interpret stages in their function context, not as one
global monotonic counter. Channel allocation failure can leave entry stage 20.

Each engine invalidates its stage to zero before publishing result and stage,
so a reset during that update cannot present a new result as a completed old
stage. Initcall updates similarly publish state last. These are bounded MMIO
stores and barriers, not an atomic multi-field snapshot or a complete event log.
Per-device probe serialization and PID1 ownership separate the writers.

## RAM-runtime markers

A root-only, fixed-command misc device accepts exactly two bytes: one of `1–5`
or `A–C`, followed by newline. It has no read, ioctl, address selection or
arbitrary data-write operation and requires `CAP_SYS_ADMIN`. The guarded helper
refuses writes before mapping readiness or with a mismatched trace header.
Ordinary profiles do not register this interface.

Packaging changes only the trace ramdisk: bootstrap and USB reporter write their
assigned markers; original Android init starts a one-shot startup check instead
of the rendering service. Reporter stage 2 is published once so reconnects cannot
erase evidence of an accepted request. `/system` remains the copied RAM runtime,
`/data` and `/cache` remain tmpfs, and no Android block filesystem is mounted.
The proprietary library files are retained for a controlled runtime comparison
but the trace service never loads the rendering probe.

## Retrieval and limits

After a boot-only trace test, restore original boot and verify complete boot and
recovery hashes first. `scripts/retrieve-gpu-startup-trace.py` rechecks the working
original kernel, boot completion, both full hashes and live memory-map ownership.
It deploys the existing SHA-pinned ARM reader only to `/dev` RAM, takes **one**
read-only 128-byte snapshot via its tested `mmap2()` path, unmaps/closes before
output, removes the temporary reader and checks unchanged original boot ID/logs.
No direct `/dev/mem read()`, retry, wider mapping or fallback is allowed.

`scripts/decode-gpu-startup-trace.py` requires exact length, SMP magic/version,
cookie 49, unchanged reserved words and an initcall address in the matched
kernel's `System.map`. Raw identifiers/logs stay private. Cookie 49 identifies
this build, not a unique boot; maintain the attempt record and reject old data.
The retrieval wrapper also requires the attempt's saved artifact-verification
record: the candidate image identity, appended-kernel hash and `System.map` hash
must match the outputs checked against the completed build. A wrong image or
symbol map is rejected before any ADB read or RAM-reader deployment.

This starts at the existing early Tegra IO mapping, **not** in the decompressor
or pre-MMU entry. Missing/invalid data cannot establish where execution stopped.
A last-entered function narrows observed progress; it does not prove that
function caused the stop. Other CPUs, asynchronous work, reset retention and
instrumentation timing can affect the result. Ordinary pstore/`last_kmsg` cannot
be assumed to preserve the candidate's log across restoration.

## Completed offline checks

Full ARM zImage and DT builds pass. Actual linked ARM reset code passes the
cookie-49 Cortex-A9 emulator tests, including wrong-header/other-CPU rejection
and IRAM bounds. Actual C trace helper/writer tests cover all offset and command
bounds, missing mapping, stale headers, capability and copy failures. Decoder
tests reject corrupt/stale records and wrong symbol maps. Reader orchestration
tests reject wrong original kernel/hash/occupied memory before mapping, and
remove the reader after stale data, unstable snapshots or new faults. The
unchanged reader passes its nine compiled ARM syscall scenarios.

The packed image passes boot-header/payload/hash, no-rendering invocation,
RAM-only mounts, marker and exact-DT checks. Existing host probe, clock, reset,
client-deferral and framed-report regression checks pass. These are offline
checks, not physical acceptance or evidence of a corrected boot.

The untraced GPU control also rebuilds. Its resolved configuration differs from
candidate 48 only by the new trace option being explicitly disabled, and its
symbol map omits the trace device. Patch replay and the compiled source mirror
match kernel commit `28b2e28a` exactly.

Accepted local candidate:
`artifacts/gpu-startup49-v3-ready/wingray-gpu-render-diagnostic.img`, 5,881,856 bytes,
SHA256 `2cb257c0fe6957b6041a9fc91213ff921a8a4c8533ce2cd99af5212e28ad3eca`.
Build with `XOOM_PROFILE=gpu-startup-trace`; package with
`scripts/prepare-gpu-render-diagnostic.py --startup-trace` and fresh directories.
No recovery write or partition-layout change is part of this experiment.
