# Image 26: exact GPT option parsing and relocated-table evidence

Prepared 21 October 2026. Continues image 25, retaining its hardware-confirmed
raw eMMC capacity correction and the same framed-v2 RAM diagnostic/runtime.

## Verified mechanism and correction

Image 25 reports the original kernel's 62,521,344 sectors, but no partitions.
Its compiled setup table puts the broad `gpt` handler before `gpt_sector=`.
`obsolete_checksetup()` matches prefixes and stops on a nonzero handler return;
`force_gpt_fn()` previously accepted every suffix. A compiled test using the
actual dispatcher and handlers reproduces `gpt_sector=0x03b9dfff` being consumed
without setting the relocated sector. The boot command line contains this value.
The previously reduced capacity masked the defect because the valid alternate
GPT was at the apparent disk end.

Patch 0043 / donor commit `43016120` accepts only the bare `gpt` token, leaving
longer options for their handlers. It also logs a relocated-GPT attempt inside
the existing board/controller/force/range gates. Normal GPT header/entry CRC
validation remains unchanged. Patch 0044 / `47d284e7` separately changes the
trace cookie to `0x584d001a`.

The actual dispatcher/handler regression passes with either setup order, bare
`gpt` before/after the sector, decimal/hex values, invalid suffixes and invalid
values. The controlled number parser models these inputs; it is not a full test
of the kernel's numeric conversion library. The eight actual-source GPT
selection cases also pass; their media and CRC validators are stubbed.
Full minimal diagnostic build and boot-image structure audit completed. The DTB equals image 25 byte-for-byte and configuration differs only by the
expected cookie. The RAM
diagnostic scripts and pinned static runtime hashes equal image 25 exactly.

Image SHA-256:
`18d1011e9954a130761885f27991999b8781505a142b4fdd2f89b1ee4051771d`.

## Hardware gate

Fresh preflight verifies exact Wingray identity, completed original Android boot,
AC power, 100% battery, complete boot/recovery originals, and live capacity plus
all ten partition extents. Boot-only test, fixed read-only diagnostic reports,
then original restoration and complete readback verification.

Require two fresh integrity-verified reports showing the relocated GPT attempt,
62,521,344 sectors, all ten expected BigPart extents, virtual filesystems only
and no new MMC read errors. No Android mounts, raw writes, GPT repair, recovery
write, repartition or reserved-RAM mapping is included.

## Physical result: storage-discovery gate passed

Two independently requested reports across close/reopen passed nonce, length,
SHA-256 and completion checks. Each is 36,201 bytes, with different request
nonces/checksums and snapshot uptimes about 112 and 121 seconds. Both required
zero storage-wait seconds. The kernel logs:

- Wingray preserved eMMC sector count 62,521,344.
- Relocated GPT attempted at sector 62,513,151 at approximately 0.702 seconds.
- The alternate GPT was accepted by normal validation and the Wingray BigPart
  view was selected. All ten partitions appeared.

The complete capacity and all ten start/size pairs match the fresh original
Android-kernel reference. Both reports contain virtual filesystem mounts only.
The reviewed reports show no MMC read timeout or I/O error. Existing diagnostic
warnings (initial GPIO-provider deferral, missing explicit vmmc/vqmmc supplies,
SDHCI maximum-block-size fallback) remain; this test does not validate regulator
control, suspend, high-speed stress or full storage reliability.

The original boot image has been restored. Complete boot and recovery readbacks
match their preserved originals, Android boot completed and its boot ID remained
stable during verification. No reserved-RAM mapping or Android filesystem mount
was performed. This passes discovery and geometry only: Android startup,
filesystem integrity, full I/O reliability, display/input and power management
are still unverified.
