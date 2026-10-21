# Image 25: Wingray eMMC capacity correction

Prepared 21 October 2026 after image 24's fresh USB reports. This continues the
existing Linux 4.4.147 port and BigPart view.

## Evidence and correction

Image 24 found all ten partitions with the working kernel's exact live start
and size pairs. Its disk capacity was 62,513,152 sectors, compared with
62,521,344 from the original Android kernel: a 4 MiB discrepancy. The donor
MMC decoder subtracts `EXT_CSD_BOOT_MULT * 512` from large nonremovable cards;
the working kernel uses raw `EXT_CSD_SEC_CNT`. The measured difference matches
the combined exposed boot-area sizes. Raw EXT_CSD was not independently read.

Patch 0041 / donor commit `9f022b09` preserves the raw count only when the root
board is `motorola,wingray`, the host is nonremovable, and its parent controller
has `motorola,xoom-bigpart`. Other hosts retain the donor policy. Patch 0042 /
`4429e5b8` separately identifies this build with cookie `0x584d0019`.
No clock, voltage, reset, tap timing, partition extent or on-disk GPT changes.
The fixed PING/REPORT-only framed diagnostic is identical to image 24.

The existing scoped GPT fallback can read the bootloader's relocated GPT at
sector 62,513,151 even with the original kernel's larger apparent capacity.
It still requires normal header and entry-array validation. A GPT warning does
not authorize repairing or rewriting the table.

## Offline checks

- Full minimal diagnostic kernel build passed.
- 384 compiled actual-source capacity cases passed with undefined-behavior
  checks: board/controller gates, missing parent/node, removable cards, 2 GiB
  boundary, multiplier extremes and unchanged behavior on other hosts.
- Eight compiled actual-source GPT-selection cases passed: relocated fallback
  scope, physical-end preference, original/reduced capacities, invalid location
  gates and valid primary preference. Media reads and CRC validators are stubbed;
  these tests establish selection flow, not physical media or CRC correctness.
- Boot-image structure audit completed: load `0x10008000`, RAM disk `0x11000000`,
  tags `0x10000100`, 2048-byte pages, appended Wingray DTB, valid v0 image ID.

Image SHA-256:
`5864fa4e345cb3b849eed39c203656aeea86730d689390b18c3b599e76171108`.

## Hardware acceptance and limits

Verify exact device, wall power, original Android boot completion, full preserved
boot/recovery images and fresh live capacity/geometry before the boot-only test.
Obtain two fresh nonce/size/checksum-verified reports across port close/reopen.
Require 62,521,344 sectors and all ten partition extents matching that fresh
reference, virtual mounts only and no new MMC errors. A mismatch remains a
failure. Restore original boot and verify complete boot/recovery readbacks.
No Android partition mount, filesystem write, recovery write, repartition or
reserved-RAM mapping is part of this cycle.

## Physical result: capacity corrected, partition discovery regressed

Two fresh reports passed nonce, size, checksum and completion checks. Both show
62,521,344 sectors, and the kernel logs the Wingray raw-capacity branch. This
verifies the capacity correction on hardware. However all ten partitions remain
missing after the bounded 20-second wait. The storage gate **failed** with
`partition_set_mismatch`; no Android filesystem was mounted.

The boot command line still contains `gpt gpt_sector=0x03b9dfff`. In this built
kernel, `__setup_force_gpt_fn` precedes `__setup_xoom_gpt_sector_setup` in the
setup table. The legacy setup dispatcher uses prefix matching, while the broad
`gpt` handler accepts any suffix. Therefore it can consume `gpt_sector=...`
without calling the sector handler. Earlier capacity reduction placed the valid
alternate GPT at the apparent disk end and masked the unusable relocated lookup.
A compiled actual-handler/dispatcher regression reproduces the prefix loss.
With an exact-token guard it parses correctly in both orders, including invalid
suffix/value controls. Follow-up [image 26](trace-boot-attempt-26.md) physically
confirmed the relocated GPT and all ten partitions at full capacity.

Original boot was restored. Complete boot and recovery readbacks match their
preserved originals; original Android boot completed and stayed on the same
boot ID through verification. No reserved-RAM read was performed. This image
runs diagnostic userspace, not Android.
