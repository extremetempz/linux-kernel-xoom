# Xoom BigPart integration

The intended scheme is Xoom BigPart, not Samsung BigSys or a modern dynamic-partition layout.

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
