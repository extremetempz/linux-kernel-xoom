# Startup diagnostic 51 result

Test/readback recorded 25 October 2026 (client timezone). **The kernel rejected
its external initramfs before GPU or USB initialization. Android was restored.**

The one guarded 128-byte record matches cookie `0x584d0051` and the exact compiled
System.map. Trace SHA256: `8c0f303e72dacd5f2f4707ab3ddb2c42b3ae9d24b29b2dccbe33ebcc3593b0ab`.

- Panic prefix: `XOOM unpack junk in `. The cookie-51 diagnostic calls panic with
  this prefix only after external `unpack_to_rootfs()` returns an error.
- Last initcall: `populate_rootfs`, entered but not returned. Kernel stage 4;
  no userspace, host, GPU or USB initialization stages recorded.
- CPU1 online bit is 1; reset/C startup milestones completed.
- The absent/skipped-initrd checks did not trigger. A nonzero initrd pointer
  reached the unpacker. Its size and byte integrity were not captured.
- The EMC correction has not reached hardware execution in this test; it remains
  regression-tested software, not hardware-validated engine bring-up.

Both complete original boot/recovery hashes match after restoration. The guarded
readback completed without a new detected kernel-log fault; its temporary RAM
reader was removed. No restoration remains pending. Private raw evidence:
`artifacts/gpu-startup51-attempt1/`.

## Follow-up source investigation

GNU cpio extracts the generated regular files. The actual Linux streaming cpio
state machine also accepts the intended decompressed archive offline, including
32 KiB chunks used by the gzip flush callback, 4 KiB chunks and one complete
buffer (filesystem calls stubbed; this checks parser state, not real filesystem
behavior or the kernel decompressor). These checks do not prove the bytes that
reached hardware or the runtime decompression output.

Next isolate byte integrity/length of the bootloader-supplied compressed initrd
before changing archive format or blaming the bootloader. A bounded fingerprint
can distinguish changed input from the intended image; a match alone is not a
cryptographic proof of equality. Keep rendering disabled until startup succeeds.
