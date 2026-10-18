# Xoom BigPart integration

The intended scheme is Xoom BigPart, not Samsung BigSys or a modern dynamic-partition layout.

The [original BigPart kernel commit](https://github.com/Schischu/android_kernel_moto_wingray/commit/6b3d70fff905b7395fd15992c3779b27d1b6c101) has now been inspected. It changes the kernel's in-memory GPT view, leaving the on-disk GPT unchanged. For Wingray, in 512-byte sectors, the original system/cache/userdata starts are `0x1d000`, `0x9d000`, `0xf1800`. System expands from `0x80000` to `0x200000` sectors; cache expands from `0x54800` to `0x100000`; userdata shifts by `0x22b800` sectors and shrinks by the same amount. Its end stays fixed. This explains why recovery and kernel must use the same view.

The new 4.4 implementation is gated by the Wingray DT identity and `motorola,xoom-bigpart` on the eMMC controller. It checks the complete legacy triplet, duplicate entries, bounds and overlaps before publishing any remapped entries. It rejects unrecognized and physically rewritten GPT layouts rather than guessing. These constants reproduce the source behavior; the owner's actual GPT and filesystem placement still need a read-only comparison before use.

Original resource thread identified through a historical installation guide:
[XDA thread 2580256](https://xdaforums.com/showthread.php?t=2580256).
Historical [Wingray OmniROM thread 2506997](https://xdaforums.com/showthread.php?t=2506997) and [linking guide](https://ok521.wordpress.com/2016/06/) provide context. Direct retrieval of the BigPart XDA thread failed during this research; its current attachments, exact procedure and checksums have not been verified. Do not treat this document as repartitioning instructions.

The preserved Wingray Marshmallow BoardConfig declares:

| Image | Bytes |
|---|---:|
| system | 1,056,858,112 |
| cache | 528,429,056 |
| userdata | 29,859,115,008 |

These are build settings from one upstream tree, not measured geometry for the owner's device. Do not infer offsets, boot/recovery sizes or partition numbers from them. The legacy board identifies itself as `stingray` in several paths even on Wingray; inspect rather than mechanically renaming these.

Before integration, obtain the original BigPart recovery and matching kernel/boot handling, record SHA-256 and provenance, and compare their source partition mapping with the running tablet. Record `/proc/partitions`, `/proc/cmdline`, mount output, recovery fstab, block sizes and kernel configuration. Keep backups of boot, recovery and data off the tablet.

Recovery, kernel partition enumeration, Android fstab, image limits and installer checks must all agree. This legacy Tegra scheme may depend on downstream parsing and boot arguments; a modern GPT assumption is unsafe. Carry the required behavior into the 4.4 port after source comparison.

BigPart migration formats internal storage. Any existing BigPart install should be identified before considering a migration. No script in this repository repartitions or flashes anything. Validate expanded ext4 image size against the measured system partition, including filesystem overhead; a small compressed ZIP is not evidence that the image fits.
