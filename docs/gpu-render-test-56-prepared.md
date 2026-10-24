# Rendering diagnostic 56: explicit USB release and working writev markers

Prepared 25 October 2026. **Not flashed or hardware-tested yet. Linux 4.4
acceleration remains unproven.**

Patch 0106 fixes the reproduced diagnostic writev-fragment rejection. Patch 0107
adds a fresh profile/cookie `0x584d0056` and fixed numeric channel progress
checkpoints. Functional GPU code, return values, resource layout and clock limits
are unchanged. Preserve successful startup-only build 54 and rendering attempt55.

The same original NVIDIA two-frame probe and runtime are embedded in the kernel.
The service first confirms property workspace and device nodes, then waits up
to 300 seconds for a RAM release flag. It does not enter the EGL child at boot.

1. Capture and verify a fresh USB baseline with ordinary `PING`/`REPORT`. These
   requests do not create the release flag and remain read-only.
2. `scripts/release-gpu-probe.py` requires the verified baseline, active candidate
   state and expected gadget before sending the one fixed `GPU_RUN <nonce>`
   command. No user-provided shell command/path is transmitted.
3. The server validates the nonce, requires the waiting service, and releases
   only the already-configured child. Repeated releases return `ALREADY` and
   cannot launch another child. A ready timeout returns no rendering result.
4. Keep the existing 20-second alarm and independent 35-second child kill limit;
   capture another report after completion. An uninterruptible kernel wait may
   still defeat userspace timeouts; retain the button/restore path.

The retained engine slots now record channel open (0x400–0x403), write
(0x410–0x412), pin/submit (0x420–0x423), and ioctl entry/return
(0x500/0x600 + command number). Errors remain unchanged. These are progress
markers, not proof of completed GPU work. The ordinary tested profiles compile
them out. Existing reserved-memory bounds and the read-only retrieval helper
are unchanged.

Image SHA256: `db5822633d9d807d18ce75a713e0b6e72cd8a6d254dc9039062aa26e6ed1eb55`; 5797888 bytes. Source `c8656ad0` includes the
separate writev correction `deca8957`. Tests passed: full ARM build and symbol/DT
checks; actual ELF-linked runtime and Image identity; conservative footprint bound;
image/dependency/child-preload/timeout gates; actual writev, privilege and command
fixtures; ARM reset emulation; existing job lifetime/publication/deferral checks;
and actual packed server/worker PTY integration with inert fake GPU devices.
The PTY test confirms no pre-release child, no side effects from PING/REPORT,
malformed/injection rejection and idempotent release. It does not test real GPU.

User requested commits before flashing. Publish code, separate patches and
findings to private main before rebooting/flashing this candidate. Then fresh
power/original-image preflight, boot-only test, original restoration and complete
readback are required. No persistent mounts, Samsung board data, new driver
implementation, DRAM-rate or voltage changes are introduced.
