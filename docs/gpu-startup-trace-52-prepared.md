# Startup diagnostic 52: fingerprint external initrd input

Prepared 25 October 2026. Not yet hardware-tested. Trace 51 proved that the
external archive unpacker returned an error before GPU/USB initialization.

The unchanged intended archive passes the actual kernel cpio streaming state
machine offline at 32 KiB, 4 KiB, 113-byte and full-buffer flush sizes; corrupt
magic is rejected. Filesystem calls are inert stubs, so this does not test the
kernel gzip decoder, device memory or real filesystem behavior.

Patch 0102 adds only a cookie-52 diagnostic. Before external unpacking it records
the compressed input length and a CPU-only FNV-1a fingerprint in the kernel log.
If unpacking fails, the complete pair fits the existing 20-byte retained panic
prefix: `RD <8 hex fingerprint> <8 hex length>`. No reader or reserved-memory
layout change is required. Zero or greater-than-16-MiB lengths are rejected before
the extra read. This does not change ramdisk placement or archive format.

Expected compressed length: **3278629** (`00320725`).
Expected FNV-1a32: **`cb109045`**. A mismatch establishes changed
input or length; a match is not a cryptographic proof of complete byte equality.
An unchanged pair would shift investigation toward runtime decompression/parser
behavior. No bootloader cause is presumed.

Image SHA256: `f5f4c5ef91e784c1daf8ed076c2cd75bfe8dbff70a1a8f68c66e3fc14cb86c15`; 5883904 bytes. Kernel source
`bed8efa2`; ramdisk SHA256 remains
`54bc23da30e3b4e17a87f461aac2e80bcf85bdbdcd17fc43230864f5a2b65c7a`. Rendering stays disabled. Board DT, image load
addresses, clock safety guards and original images are preserved.

Build/config/DT/symbol gates, byte comparison against compiled outputs, actual
fingerprint/length/failure branches, retained bounds/metadata decoder, image
payload checks and ARM reset emulation passed. Original-image preflight, boot-only
flash, evidence retrieval, original restoration and full readback remain required.
