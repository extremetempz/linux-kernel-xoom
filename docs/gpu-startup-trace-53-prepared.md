# Startup diagnostic 53: controlled ramdisk relocation

Prepared 25 October 2026. **Relocation is an unproven experiment, not a confirmed
boot fix. Rendering remains disabled.**

Trace 52 received the intended initrd length but a different FNV-1a fingerprint,
then failed unpacking. This test changes its Android boot header ramdisk address
from `0x11000000` to `0x12000000`. The compressed ramdisk is byte-for-byte identical.
The functional kernel/DT/configuration remains the same, except for a fresh
cookie `0x584d0053` and equivalent trace guards; patch 0103 separates that identity
change. A new cookie prevents accepting trace 52 as a result of this test.

The common tested image packer is unchanged. The experiment changes only the
ramdisk-address field of the newly packed control image; payload, padding, other
header fields and component SHA1 ID are identical. The packing gate restricts
relocation to startup diagnostic 53 and the single reviewed alternative.

The range `0x12000000` through `0x12320724` lies inside
the original kernel's `0x00000000..0x1fdfffff` System RAM bank. It avoids known
kernel text/data, framebuffer/video/generic carveout and reserved-trace regions.
This establishes compatibility with the known memory map, not the undocumented
bootloader's internal workspace or whether it honors the header address.

Image SHA256: `c6d4bf3f6442675f5ea4486f18bcd4a6b135c98e98813b14b76693d0a5587524`; 5883904 bytes. Expected compressed input is
3278629 bytes, FNV-1a32 `cb109045`. A matching fingerprint
is only a consistency check; startup and live USB evidence are still required.

Full ARM build, unchanged-DT/payload/header/config/symbol gates, byte comparison
with saved compiled outputs, actual cookie-53 fingerprint/panic/writer/decoder
fixtures and ARM reset emulation passed. Fresh original-image/power preflight,
boot-only hardware observation, original restoration and complete hash readback
remain required. Preserve the old-address images and all tested configurations.
