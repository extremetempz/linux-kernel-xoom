# Candidate 11: sparse-progress repeatability check

Status: built, statically checked and physically tested. The original boot and
recovery images were restored and verified; the new kernel did not reach
Android.

Candidate 11 keeps candidate 10's kernel behavior and one progress store per
512 PFNs. Only the trace cookie changed (`0x584d000b`), to check whether the
last sparse checkpoint repeats over a longer observation. The planned maximum
observation was five minutes; fastboot reappeared after about three minutes,
so the test ended before that limit.

## Build and preflight

- Donor source commit: `11be3f00` (`ARM: tegra: prepare five-minute sparse trace candidate`).
- Root patch: `kernel/patches/0016-wingray-trace-cookie-11.patch`.
- Trace enabled; sparse page progress enabled; detailed page tracing disabled.
- Kernel and appended-DTB build completed with the pinned Android GCC 4.9 toolchain. The ARM entry, ATAG/MMU, allocator, memmap, fatal-path and reader-emulation tests passed.
- Diagnostic image SHA-256: `57c0fa50e9d335b43621bffca43189577b223012feb2c1d0663aaab06c0f63e3`.
- Android boot v0, 2048-byte pages, kernel load `0x10008000`, ramdisk load `0x11000000`, tags `0x10000100`; the image audit confirmed a valid appended Wingray DTB. These image declarations do not capture bootloader register state.
- Immediately before testing, rooted Android identified `wingray`, bootloader 1050, kernel `2.6.39.4-ElementalX-Xoom-2.1+`, and `sys.boot_completed=1`. Complete live reads of boot and recovery matched their preserved images byte for byte.

## Hardware result

Fastboot identified the device as unlocked `xoom-wifi`. The candidate was
written to the `boot` partition only; fastboot reported success.
The tablet remained at the Motorola logo. About three minutes after reboot,
Google Fastboot (`18d1:708c`) enumerated on USB. No diagnostic USB serial or ADB
device appeared. The observation does not determine whether the return to the
bootloader was automatic or button-driven.

The original boot image was then restored and Android rebooted. Full live reads
of boot and recovery matched the preserved originals:

- Boot SHA-256: `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Recovery SHA-256: `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.
- Android 4.4.4 with Linux `2.6.39.4-ElementalX-Xoom-2.1+` reached `sys.boot_completed=1`.

## Trace and interpretation

One bounded read-only snapshot returned a valid format-2 record with the
expected cookie `0x584d000b`. Entry, ATAG conversion, decompression, MMU
handoff, kernel C entry, machine selection, and the marker before `paging_init`
were present. The last phase was `0x9002ebff`, the sparse checkpoint after
processing PFN `0x2ebff` (physical page `0x2ebff000`). The zone-loop return
marker `0x703`, enclosing `memmap_init` return marker `0x516`, and first-fatal
PC were absent. `tegra_init_early` and the early-initcall marker were also
absent. This identifies the last sampled progress, not an exact faulting PFN
or address; unsampled loop work after `0x2ebff` is not recorded.

Candidate 10 had the same last sparse checkpoint (`0x2ebff`) with its own
matching cookie. That repetition supports a stable last observed point under
this sampling profile, but it does not prove a fault or permanent hang. Earlier
profiles reported later checkpoints (`0x2ec03` and `0x2ec7f`) with different
instrumentation frequency, so their PFN values cannot be compared as though
the runs had identical timing or code paths.

The trace transport had no stderr, Android's boot ID did not change during
retrieval, dmesg was identical before and after, and no temporary reader was
left on the tablet. Raw images, trace bytes and logs remain local under
`artifacts/trace-boot-attempt-11-prepared/` and must not be uploaded.

The next diagnostic should record the containing zone's bounds and add
lower-frequency checkpoints only inside the previously observed PFN band,
without changing the page initialization operations. It should separate
progress within that band from a loop return before any allocator or memory-map
behavior is changed.
