# Build 56 readback: runtime and request parser reached; GPU not released

Readback recorded 25 October 2026 (client timezone), after the user manually
restored the original boot image. **Build 56 reached userspace and parsed a
valid diagnostic request. No GPU release command was sent by this session,
and no rendered result was recovered.**

## Verified retained record

The single guarded snapshot matches cookie `0x584d0056` and the compiled
System.map. Trace SHA256 `0525aac7de60ad6d2a8b710d03dee795331824eed0b931b0eaffddbdcc39ab27`; map SHA256
`336b7fd7b9509cc411926bb520db94dcea4409228e926fe8c381d7c1dc1fb6e8`.

- CPU1 reset/C startup completed, result 0, online bit 1.
- Host, GR2D and GR3D initialization: stage 61/result 0. No subsequent
  channel open/write/submit/ioctl stage was recorded.
- Kernel stage 7/exec result 0: the early init executable was entered.
- Userspace stage 3: the GPU service entered its script. This marker precedes
  property/device checks and the release gate; it does not establish that those
  checks passed, that the gate was reached, or that the service remained alive.
- Reporter stage 3: the server parsed a recognized request with a valid nonce.
  In the saved host handshake, only readiness PINGs were sent before timeout;
  no REPORT or GPU_RUN request was reached. This establishes request-parser
  progress, not successful response transmission or receipt.
- USB registration returned 0; no panic was recorded. The final PID1 initcall,
  `clk_disable_unused`, returned 0.

The userspace/reporter markers now contain valid progress, unlike builds 54/55.
This is hardware evidence that the corrected vectored command writer can record
userspace progress. It is not GPU execution evidence.

## Host observation and limits

The diagnostic ACM gadget enumerated as `/dev/ttyACM0`, but the saved readiness
handshake timed out after receiving zero serial bytes. The device-side parser
checkpoint shows that absence of a host reply must not be interpreted as no
userspace or no incoming request.

The record does not bracket the readiness-response write or store its return
value. It cannot distinguish a device-side write stall/failure, later reporter
exit, USB gadget transmit problem, or host/VM receive/framing issue. No one of
these is established as the cause. There is no evidence here for a GPU driver
fix or a successful rendering run. The bounded GPU release tool was never run.

The next useful diagnostic should bracket the fixed readiness reply and record
its write result, while retaining the no-GPU-before-verified-baseline gate. If
the device completes the write, investigate gadget/host receipt; if it does not,
localize that write path. Avoid another immediate rendering attempt without
first recovering a verified USB baseline.

## Device preservation

ADB confirmed the original `2.6.39.4-ElementalX-Xoom-2.1+` ROM and Android boot
completion. Complete original boot and recovery hashes match their preserved
backups. The user performed restoration; no partition was flashed during this
readback session. The temporary reader was removed, boot ID remained unchanged
through the read, and no new original-kernel fault was detected in the log
comparison. No restoration or GPU release remains pending.

Private raw evidence: `artifacts/gpu-render56-attempt1/`; failed host handshake:
`artifacts/gpu-render56-baseline/`. The normal ROM's saved `last_kmsg` is not
assumed to contain the Linux 4.4 diagnostic's full kernel log.
