# GPU rendering attempt 48: no diagnostic result

24 October 2026. Candidate
`5bdf90ce7f02616e3970d26cf5d2f26ee2a598d9741dbb8f86194158a13421f0`
was flashed to boot and rebooted. Fastboot acknowledged both transfer and write.
The operator reported the Motorola logo. The guest observed neither a diagnostic
USB device nor a serial node, including after the operator reconnected the cable.
No framed rendering report was captured. **Linux 4.4 acceleration remains unproven.**

The screen is intentionally unchanged for this offscreen-only runtime, so the
logo is not itself evidence of a kernel hang. The missing USB result could reflect
an earlier kernel/engine stop, runtime failure or a USB/VMware problem. These
possibilities have not been distinguished. Offline fault tests and a successful
build do not establish which occurred on hardware.

## Restoration verified

The first restoration precheck saw no fastboot device and performed no write.
After the operator reconnected fastboot, the original boot write and reboot
succeeded. The working original Android kernel and boot completion were verified.
Complete live boot (8 MiB) and recovery (12 MiB) SHA256 hashes match their pinned
original backups. Recovery and the partition layout were not written.
No restoration remains pending. Battery was 65% at preflight.

The read-only `/proc/last_kmsg` capture is 89,760 bytes and identifies
`2.6.39.4-ElementalX-Xoom-2.1+`; it is not the failed candidate's log and supplies
no candidate fault location. It must not be used to diagnose this stop.
Private logs/state are retained in `artifacts/gpu-render48-attempt1/`.

## Next diagnostic gate

Preserve this candidate and the successful host-only image. Do not change GPU
rates, rails, Samsung board controls or submission semantics based on this result.
Before another combined test, obtain retained early/initcall checkpoints or run
a staged control that establishes USB/runtime operation before engine activation.
That should distinguish CPU/kernel startup, host initialization, GR2D/GR3D reset
and publication, original-init startup and first userspace submission. A missing
or stale retained record must remain an unknown, not a claimed failure location.

Only after that gate should the same two-frame NVIDIA readback probe be retried.
Accelerated framebuffer composition and synchronization remain later work.
