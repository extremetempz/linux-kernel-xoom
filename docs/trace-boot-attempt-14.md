# Candidate 14: correct low-memory zone sizing after no-map removal

Prepared 20 October 2026. The build and offline checks passed; the physical
boot-only test, original restoration and trace retrieval are complete.

## Source-level defect

`sanity_check_meminfo()` determines `arm_lowmem_limit` before
`arm_memblock_init()` scans DT reserved memory. Wingray's DT subsequently
removes the top video range `[0x2e800000, 0x40000000)` from usable RAM.
`paging_init()` maps the remaining banks but sets the allocation ceiling to
the older `arm_lowmem_limit`. `find_limits()` previously used that ceiling
as `max_low`, independently of the lower actual end of remaining DRAM.

For the Xoom fixture with ceiling PFN `0x30000`, end PFN `0x2e800` and first
PFN 1, the old production code produces:

- Normal zone size `0x2ffff` PFNs, ending at `0x30000`.
- HighMem zone size `0xffffe800` PFNs: unsigned `0x2e800 - 0x30000`.
- Combined node span wraps to `0x2e7ff`, ending at `0x2e800`.

The flat descriptor array is sized from the combined span, but the Normal
zone initialization loop extends beyond that allocation. With the base and
stride recorded by candidate 13, the first out-of-bounds descriptor at PFN
`0x2e800` calculates to virtual `0xee7f7000`; the descriptor at PFN `0x2ec80`
calculates to `0xee800000`, corresponding to the video no-map boundary under
the intended linear translation. This explains the address correlation in
candidate 13 at the source/arithmetic level. The actual failing instruction
and candidate 13's live `max_high` were not captured, so hardware causality
still requires the corrected candidate's result.

## Correction

Cap the lowmem PFN limit at the remaining DRAM end after reading both values
in `find_limits()`. This prevents unsigned HighMem underflow and keeps the
Normal initialization span inside the node's allocated descriptor range.
Keep HIGHMEM enabled, the framebuffer/video reservations, RAM banks and
allocator operation order unchanged. This correction is isolated from the
fresh diagnostic cookie (`0x584d000e`).

Patch `0019-arm-cap-lowmem-after-nomap.patch` contains the sizing correction;
patch `0020-wingray-trace-lowmem-fix-cookie.patch` contains only the cookie.

## Regression evidence

`tests/test-wingray-memory-limits.py` extracts the actual production
`find_limits()` and `zone_sizes_init()` bodies and compiles them with the
pinned ARM compiler. Cortex-A9 emulation executes the resulting 32-bit code
against controlled bank metadata, capturing the actual zone-size arguments.
It reproduces the old underflow and descriptor-span overrun for the Xoom
layout, small-RAM and unaligned-top-removal cases. The corrected code passes
all six layouts, including real highmem, exact-lowmem and hole-containing
RAM. It checks zone ordering, total span, hole counts and page accounting.
The fixture does not emulate memblock allocation, kernel mappings or DRAM.

The donor derives this sizing code from upstream ARM Linux; the same
unbounded ceiling appears in the [Linux v4.4 source](https://github.com/torvalds/linux/blob/v4.4/arch/arm/mm/init.c).
The presence of the upstream code does not make every board affected: it
requires a remaining DRAM end below the earlier lowmem ceiling.

## Hardware plan and result

Build, ARM/DTB checks, boot-image audit, 14 compiled memmap scenarios, four
compiled real pageblock scenarios and 48 MMU snippets passed. The compiled
converter/start-kernel checks also passed. Full original boot/recovery
readbacks and AC charging were verified before the boot-only flash. Fastboot
reported successful candidate write and reboot. The two-minute observation
completed, the original boot image was restored and Android returned. Full
boot/recovery readbacks match their preserved originals. One bounded read-only
trace retrieval succeeded; Android remained running with unchanged boot ID
and identical dmesg. The temporary reader was removed. Retain the minimal trace profile
for this first test so the sizing correction can be assessed without new
peripheral probes. It cannot boot Android with block and USB disabled.
A successful memmap return is the gate for a separate USB/storage diagnostic
and subsequent Android integration. Do not claim a complete Android kernel
from offline checks alone.

See [Android startup gates](android-boot-gates.md) for the separate storage,
Binder API, device-path and graphics-ABI work required after memory setup.

## Physical trace result

The format-2 record is valid with fresh cookie `0x584d000e`. Its active Normal
zone is now `[0x1, 0x2e800)`, rather than candidate 13's `[0x1, 0x30000)`.
The first descriptor remains `0xee227020` with a 32-byte stride. This confirms
that the remaining-RAM cap took effect on the tablet.

The latest phase is `0x401` (`setup_arch_returned`). The retained
`tegra_init_early` and early-initcall markers are both present. These later
stages require paging and early zone initialization to have returned: the
memory stop from the earlier runs has been passed. The single phase slot no
longer retains the intermediate loop-return checkpoint.

The first-fatal word is `0xbad00001`, a panic recorded after further startup.
The existing record contains no panic text, so the new cause is unknown.
This is a successful advance beyond the old memory failure, not a successful
Android boot. The next candidate should add panic-reason capture and USB
logging, retaining the corrected memory sizing.

Original restoration hashes:

- Boot: `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Recovery: `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.

Kernel-plus-DTB SHA-256:
`804d2a9aa07539d6ca32f33f9495a71721b39289a5ed780e96705676f44b4cfb`.
Diagnostic-image SHA-256:
`b6a5f18583c217c0f07f1754b79df56a84b1e4ef6ccbd610a1d3592798517b9a`.
Raw evidence remains local in `artifacts/trace-boot-attempt-14-prepared/`.
