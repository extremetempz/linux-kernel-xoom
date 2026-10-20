# Candidate 13: page descriptor and boundary checkpoints

Prepared and rechecked 20 October 2026. The diagnostic boot-only flash succeeded and
the two-minute observation interval completed. The original boot image has
subsequently been restored through fastboot. Android startup, full boot and
recovery readbacks, and the single bounded trace retrieval all passed.
Candidate 12 was prepared but was not physically tested.

## Evidence and purpose

Candidate 11 last recorded sparse progress after PFN `0x2ebff` in
`memmap_init_zone()`. It did not record that function returning. This does not
identify a faulting instruction, bad PFN, or cause of the stop. Earlier profiles
reached different nearby checkpoints, so tracing overhead remains a possible
influence.

Candidate 13 retains candidate 12's active-zone bounds and four possible
16-page progress samples in `0x2ebf0..0x2ec2f`. It also records the first page
descriptor address and compiled descriptor stride. Six checkpoints at PFN
`0x2ec00` bracket the PFN predicates, single-page initialization, and pageblock
bitmap update. No instrumentation is inserted inside the exclusive-access
instruction sequence. Memory banks, allocator operation order, and boot image
load addresses are unchanged.

The new `0x58` tagged zone record reuses four earlier MMU-handoff words only
after paging, within the existing 128-byte trace. The decoder retains support
for candidate 12's `WMAP` record. A calculated descriptor address is arithmetic
from recorded zone metadata, not a captured fault address. Fresh trace cookie:
`0x584d000d`.

## Build and verification

Source correction is isolated in donor commit
`a940c82e0ccc4a1d959bc4f389ae2f8db88d89d6`, exported as
`kernel/patches/0018-wingray-trace-page-boundary.patch`.

The trace profile rebuilt successfully at its original build path and matched
the prepared kernel byte-for-byte. Its combined `zImage-dtb` SHA-256 is
`db8e34851fb79c61bffeeb867cc8eb810bfbeff7b8fa44a9f19e22b1b25712ae`.
The diagnostic boot image SHA-256 is
`f3fb4bd543bc599ca6f5a33a31c6e7189cd70f413252e3c8c605b0f08f5e36ae`.
Absolute build-path strings are embedded in this old kernel: an otherwise
identical build at another path is not byte-for-byte reproducible.

Boot-image audit passed: version-zero header, 2048-byte pages, declared kernel
load `0x10008000`, ramdisk `0x11000000`, tags `0x10000100`, valid appended DTB,
and fixed decompression address `0x8000`. The trace-disabled early profile also
built successfully.

Rechecks passed for the decoder and all 14 compiled memmap scenarios. Four
additional scenarios execute the actual compiled pageblock bitmap update,
including LDREX/STREX, with valid emulated page/zone/bitmap storage. They verify
bitmap results, preservation of unrelated bits, bounded writes and function
return. They do not emulate real hardware cache attributes, address
translations or the real allocator's pointer validity. Passing them does not
establish the cause of the hardware stop.

## Hardware procedure and limits

Read-only preflight confirmed the original Android kernel and completed boot,
AC charging, and full byte-for-byte boot and recovery readbacks matching the
preserved originals. Battery was 16%, with the wall charger detected.

The authorized test writes boot only, observes for two minutes, restores the
original boot image, verifies full boot/recovery readbacks and Android startup,
then retrieves one bounded read-only 128-byte trace. Recovery, partitions and
Android data must remain untouched. Raw images, serials and runtime captures
remain private local artifacts.

This trace profile has block, networking, input and USB disabled. It cannot
boot Android or enumerate USB serial. A static Motorola logo cannot distinguish
its internal progress. The next decision must use the restored-ROM trace and
fresh cookie, not the screen alone.

## Hardware result and restoration

The boot-only flash, two-minute observation, original boot restoration and
reboot all succeeded through fastboot. No recovery write occurred. Full live
boot and recovery readbacks then matched the preserved originals byte-for-byte:

- Boot SHA-256: `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Recovery SHA-256: `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.

Android returned on the working Linux 2.6.39.4 kernel with boot-complete set.
The first retrieval attempt found no ADB device and stopped before any
partition read or trace mapping. Once USB appeared, verification and one
bounded read-only snapshot succeeded. Android remained running, its boot ID
was unchanged, and no new fault was reported. The temporary reader was removed.
Raw evidence remains private under `artifacts/trace-boot-attempt-13-prepared/`.

## Trace: verified observations

The record has valid format 2 and the fresh cookie `0x584d000d`. Candidate 13
was the only physical attempt using that cookie in this session. Entry, ATAG
conversion, decompression, MMU handoff, kernel C entry and machine selection
markers are present. The first-fatal slot is zero; no fatal event was recorded.
`tegra_init_early` and the early-initcall marker are absent.

The active early zone spans PFNs `[0x1, 0x30000)`, node 0, zone index 0.
Its first page descriptor is `0xee227020`, with a compiled 32-byte stride.
The last phase is `0xa002ec2f`: the end-of-iteration window checkpoint after
PFN `0x2ec2f`. The loop and enclosing memmap return markers are absent.
The earlier six boundary markers are overwritten by the later phase; they
are not an independently retained sequence of events.

This is later sampled progress than candidate 11's `0x2ebff`, but does not
prove a boot fix, exact failing instruction or permanent hang. Candidate 8
already sampled `0x2ec7f` under a different instrumentation profile. Timing
and trace cost prevent treating these PFNs as equivalent hardware runs.

## New hypothesis to investigate

Using the recorded descriptor base and stride, descriptor PFN `0x2ec7f`
calculates to virtual `0xee7fffe0`, and the next descriptor calculates to
`0xee800000`. With the intended zero physical offset and linear mapping, that
boundary corresponds to physical `0x2e800000`, the start of the legacy video
no-map region in the compiled DT and framebuffer reservation in the working
ROM's memory map. Candidate 13's last descriptor calculates to `0xee7ff5e0`.

This address correlation is a hypothesis, not a captured fault or a verified
runtime translation. In particular, the early memblock allocator normally
avoids removed or reserved regions and zeroes an allocation before returning
it. The trace does not yet explain why the calculated descriptor span appears
to approach that boundary. Do not change the video reservation or force RAM
banks based on this arithmetic alone.

The next targeted candidate should record the actual mem-map allocation base,
size, physical conversion and active memblock limits; verify whether the full
allocation intersects a removed/reserved interval; and sample the descriptor
and translation around `0xee800000` without dereferencing an unverified
mapping. Distinguish the represented PFN from the memory storing its descriptor.
Only a confirmed allocation/mapping inconsistency justifies a correction.
