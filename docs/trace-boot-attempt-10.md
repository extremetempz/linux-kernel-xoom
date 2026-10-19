# Candidate 10: sparse `memmap_init_zone` progress

Status: built and statically checked; physical test completed and original
boot/recovery readbacks verified after restoration.

Candidate 9 ended at phase `0x702` (`memmap_range_ready`) after a two-minute observation. Its quiet profile intentionally had no in-loop PFN checkpoints, so that result did not show whether the loop started or progressed. Candidate 8 reported PFN `0x2ec7f`, but its 32-PFN interval created materially more trace writes. Candidate 10 is designed to distinguish lack of loop progress from a slow loop with much lower instrumentation frequency.

The only source behavior change is trace instrumentation: page metadata detail checkpoints are separately configurable and disabled; progress stores occur once for every 512 PFNs at PFNs where `(pfn & 511) == 511`. This is 1/16 the cadence of candidate 8. The trace format still stores the last sampled PFN in phase `0x9xxxxxxx`. It does not assert that the PFN is a bad physical address or that the page's payload is accessed.

## Verified before hardware test

- Kernel source commit: `db93b27b` (`ARM: tegra: add sparse Wingray page progress trace`).
- Build cookie: `0x584d000a`.
- Config: trace and sparse progress enabled; detailed page-step trace disabled.
- Kernel and appended-DTB build completed successfully with the pinned Android GCC 4.9 toolchain.
- Offline tests passed: ARM early-entry snippets (64 executions), entry-flow (32), MMU/handoff snippets (48 plus 5 converter scenarios and 2 prologues), static-map cases (4), fatal-entry cases (9), decoder (23), allocator checkpoints (30), and compiled `memmap_init_zone` scenarios (6). The memmap harness stubs pageblock updates and does not emulate real hardware MMU/cache behavior.
- Prepared image: `artifacts/trace-boot-attempt-10-prepared/wingray-diagnostic.img`, SHA-256 `dd78bbb740613b747ecfeb724343922b7a0d18877750e89a7465687550201925`.
- Header audit passed: Android boot v0, 2048-byte pages, kernel load `0x10008000`, ramdisk load `0x11000000`, tags `0x10000100`, and a valid appended Wingray DTB. The audit verifies image structure and placement declarations, not live bootloader register state.
- Preserved original boot SHA-256: `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`; recovery SHA-256: `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`. These are local backup-file hashes; re-read both device partitions before testing and again after restoration.
- Pre-flash device readback: rooted Android identified `wingray`, bootloader 1050, kernel `2.6.39.4-ElementalX-Xoom-2.1+`, and `sys.boot_completed=1`. Complete on-device reads of boot (`mmcblk0p7`, 8 MiB) and recovery (`mmcblk0p6`, 12 MiB) matched the corresponding preserved originals byte for byte. Private readbacks are retained beside the candidate image.

## Hardware test result

Fastboot identified the device as unlocked `xoom-wifi`. The live
pre-flash full-partition reads matched both preserved originals. Candidate 10
was written to `boot` only; fastboot reported the write successful. Recovery
and the partition layout were not written.

Before the planned 120-second interval completed, the tablet was again
enumerated as Google Fastboot (`18d1:708c`). During observation there was no
`ttyACM` diagnostic serial device and no ADB device. The available evidence
cannot distinguish a button-driven fastboot handoff from an automatic return
to the bootloader, and the observation duration is therefore not a controlled
120 seconds.

After restoring the original boot image, the full on-device boot and recovery
reads again matched the preserved originals byte for byte. Android 4.4.4 with
kernel `2.6.39.4-ElementalX-Xoom-2.1+` reached `sys.boot_completed=1`. The
single bounded trace read returned a valid format-2 record with cookie
`0x584d000a`. Entry, ATAG conversion, decompression, MMU handoff, kernel C
entry, machine selection and `setup_arch` markers were present. The last phase
was `0x9002ebff`: the loop completed its sampled PFN `0x2ebff`, corresponding
to metadata for PFN `0x2ebff` (physical page `0x2ebff000`). The `memmap_init_zone`
loop-return marker `0x703`, enclosing `memmap_init` return marker `0x516`, and
first-fatal PC were absent. This is a metadata PFN, not a captured fault
address.

The retrieval transport had no stderr, the Android boot ID stayed unchanged,
and dmesg before and after retrieval was identical with no new fault messages.
The temporary reader was removed. Raw images, trace bytes and logs remain
local under `artifacts/trace-boot-attempt-10-prepared/`.

## Interpretation and next test

Interpretation is intentionally limited:

- `0x9002ebff` demonstrates that execution reached the end of a sampled loop iteration. It does not prove every PFN before it was valid or identify a faulting data address.
- Missing `0x703` and `0x516` means the trace did not record the loop or enclosing memmap initialization returning. It does not establish a permanent hang because the observation interval ended early.
- `0x703` means `memmap_init_zone` returned. It does not prove the rest of boot reached Android.
- A first-fatal PC is useful only if the fatal hook itself ran and the trace cookie matches this test.
- A stale/mismatched cookie, absent USB serial, or Motorola logo alone does not locate the failure.

The next useful comparison is the same low-overhead sampling profile with a
fresh cookie and a full five-minute observation, without changing the page
allocator operation sequence. This distinguishes a slow loop from a repeatable
stall more cleanly than adding frequent stores. If the last PFN remains stable,
then capture zone bounds and bracket the specific PFN interval in a separate
candidate before changing allocator or memory-map behavior.
