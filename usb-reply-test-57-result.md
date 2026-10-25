# Image 57: USB replies verified; GPU not released

25 October 2026. Image 57 was flashed to boot only, tested, then the preserved original boot image was restored. Both complete original boot/recovery hashes match. A single guarded retained read completed and its temporary RAM reader was removed.

The host received two independently nonce-verified readiness and complete report exchanges. Each report contained 62,487 bytes; each host capture received 84,625 wire bytes. Both confirmed the full reference eMMC capacity and all ten BigPart partition geometries. The GPU service reported its property workspace, required device nodes, and `XOOM_GPU_RENDER_WAIT_USB_GATE`. No GPU_RUN request was sent, and no rendered-frame result is claimed.

The retained snapshot matches cookie `0x584d0057` and the compiled symbol map:

- Reporter stage 3: recognized request/nonce parsed.
- USB stage 4: readiness printf returned success.
- Userspace stage 3: GPU-service entry; the live reports separately establish that it reached the waiting gate.
- Panic flag 0: no panic recorded.
- Trace SHA-256: `c8bcd2a0d49b12e7f5cea487909f6502c12cb817c973f4af331c40444397d265`.

The successful host exchanges prove actual round-trip transport on this attempt, beyond local printf acceptance alone. They do not establish the cause of build 56's zero-byte timeout. Instrumentation timing, the boot, and USB/VM connection conditions differ; no functional USB-driver correction was made. This is not evidence of GPU acceleration.

## Next test: attempt 58, unchanged image 57

Reuse the exact hardware-tested image, SHA-256 `ac2267bd05b370bb3866d53cf725605c05999c8c3e5fccdd3d30394139126a5c`, with a new private attempt directory. Do not rebuild it or combine a graphics-driver change with the first explicit GPU release.

The release tool now accepts this fixed deferred candidate as well as build 56. It checks the candidate digest, pending-restoration state, verified full baseline/storage evidence and absence of a prior release. It then requests another fresh report from the current USB session before sending the fixed GPU_RUN command. It rejects a timed-out/completed worker. The release intent is recorded before transmitting the command, so an uncertain acknowledgement is never automatically retried.

Capture a fresh post-probe report and require NVIDIA/Tegra ES2 identity, two distinct successful pixel readbacks, the existing PASS marker and a successful child exit. A hang, failure or missing report remains a failed/unknown render result, even if Android can boot with software rendering. Restore and verify both original images afterward, retaining the single guarded trace read for this new attempt if needed.

The user has requested accelerated Android with the tested CPU/cache/touch/USB/storage/display features. Attempt 58 establishes the render/submission result needed for that integration. Legacy display ownership, framebuffer posting and the matched NVIDIA EGL/gralloc/HWC overlay remain separate work; existing software-rendered Welcome is not an accelerated Android result. No Samsung board power or timing values are introduced by this test.
