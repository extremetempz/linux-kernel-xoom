# Startup diagnostic 54: built-in RAM runtime

Prepared 25 October 2026. **Not yet hardware-tested. This bypasses the failing
large external-initrd path; it does not establish or fix the original corruption
cause. Linux 4.4 GPU rendering remains unproven and is disabled in this image.**

Use Linux's existing `CONFIG_INITRAMFS_SOURCE` to include the exact intended
7,033,808-byte cpio archive in the kernel. The build helper accepts only the
SHA-pinned private runtime from diagnostic 53. Nothing proprietary is added to
git. The compressed linked runtime is saved privately with the kernel artifacts.

The external ramdisk contains only a valid `TRAILER!!!` record: no files can
override the built-in root. Kernel/ramdisk/tag load addresses return to their
preserved defaults. Board DT and hardware configuration are unchanged except
for built-in initramfs source and a fresh trace cookie `0x584d0054`. The ordinary
rootfs population code handles this profile; the external-only failure hooks
from 51–53 remain restricted to their original profiles.

Image SHA256: `59b3fd06020159de3897c175c0f5ebe2ac89c3f9197423f93a5fbd21e1d317c1`; 5797888 bytes (under 8 MiB). External archive:
124 uncompressed bytes. Source commit `8d63e7c2`;
patch 0104 is separate from the prior diagnostics.

Validation passed: full ARM link, configuration/DT/symbol gates, exact built-in
cpio payload, ELF-linked runtime bytes and recorded size, zImage compressed Image
identity, conservative 16-MiB footprint bound, image header/payload/source checks,
actual trace writer/panic bounds, ARM reset emulation, EMC regression and clock
fault fixtures. No Samsung board tables, DRAM/voltage changes or storage mounts
were added. Fresh original-image/power preflight, boot-only hardware observation,
original restoration and complete readback verification remain required.

A successful USB startup would allow inspecting engine publication and clock
results before enabling a rendering probe. Failure will be read from the fresh
retained record after restoring the original. Preserve all previous artifacts.
