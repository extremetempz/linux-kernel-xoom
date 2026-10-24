# Startup diagnostic 52: external initrd input differs

Test/readback recorded 25 October 2026 (client timezone). **The external
compressed initrd fingerprint differs from the intended boot-image payload.**
This does not locate the point of alteration or prove a bootloader bug.

The guarded 128-byte read matches cookie `0x584d0052` and its compiled System.map.
Trace SHA256: `232e8991aee3e3efb6f93b25d5ab6f77547a134010175ff617c78ceaf9560981`.

| Value | Intended payload | Kernel before external unpacking |
|---|---|---|
| Length | 3278629 bytes | 3278629 bytes |
| FNV-1a32 | `cb109045` | `a8c962bd` |

Panic prefix `RD a8c962bd 00320725` retains the complete pair. The actual
fingerprint routine passed compiled known-vector and changed-byte fixtures.
A difference establishes different input, subject to the recorded execution
being correct. A matching noncryptographic fingerprint alone would not prove
complete byte equality.

The final initcall is `populate_rootfs`, entered but not returned. It panicked
after external unpacking failed. Host/GPU/USB and userspace checkpoints are
unreached; CPU1 startup completed. No GPU work was submitted, and the EMC fix
still has not reached hardware execution in this startup sequence.

After the requested minute Android was present on ADB. Both complete original
boot/recovery hashes match; the temporary RAM reader was removed, Android remained
boot-complete, and no new fault was detected in the kernel-log comparison. No
restoration remains pending. Private evidence: `artifacts/gpu-startup52-attempt1/`.

## Controlled next test

Test a different initrd header load address, with the same compressed ramdisk,
same functional kernel configuration and unchanged board DT. Assign a fresh
trace cookie so a stale record from this attempt cannot masquerade as a new
result. The alternative must fit known RAM and avoid kernel, framebuffer,
carveout and trace regions. Treat relocation as an experiment, not a proven fix.
The header address may be ignored by the proprietary bootloader; success must
be observed rather than assumed. Keep rendering disabled and preserve the
existing images and load-address baseline.
