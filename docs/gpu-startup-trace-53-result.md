# Startup diagnostic 53: relocation did not restore intended input

Test/readback recorded 25 October 2026 (client timezone). Fresh cookie
`0x584d0053`, trace SHA256 `baa42853926558e1cb1b048467fa81cf26c23411f3c1517d1cefaf5cf56acede`.

The requested header ramdisk address was `0x12000000`, versus `0x11000000` in
52. External initrd length remained 3,278,629 bytes; its fingerprint was
`ac139391`, still different from intended `cb109045`. The unpacker
failed inside `populate_rootfs`; GPU, USB and userspace checkpoints were unreached.
The changed fingerprint alone does not prove the bootloader honored the new
address. Its internal workspace and the point where input changed remain unknown.
Relocation is not accepted as a fix. CPU1 startup still completed.

The original boot was restored. Android returned over ADB after the requested
minute; complete original boot/recovery hashes match. The single guarded trace
read and temporary RAM-reader cleanup completed without a newly detected kernel
log fault. No restoration remains pending. Private evidence is retained under
`artifacts/gpu-startup53-attempt1/`.

Next use Linux's existing built-in initramfs support to bypass the failing large
external-input path. This is a boot-path workaround, not a verified corruption
root-cause fix. Retain RAM-only runtime and keep rendering disabled until startup
and engine initialization are observed.
