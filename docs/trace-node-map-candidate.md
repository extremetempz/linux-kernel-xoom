# Candidate 12: zone bounds and narrow page-progress window

Prepared 19 October 2026. This candidate is built and offline-checked, but has
not been written to the tablet. Its fresh trace cookie is `0x584d000c`.

## Why this candidate

Candidate 11 reached its last sparse progress checkpoint after initializing
PFN `0x2ebff`, inside `memmap_init_zone()`. The trace did not record that
function returning. This is the last observed checkpoint, not a confirmed
faulting PFN or proof of a permanent hang. Candidate 12 records the active
zone's exact bounds and adds a small number of progress samples around that
checkpoint. It does not alter the memory map, page descriptors, allocator
operation order, boot parameters, or device drivers.

## Trace changes

At `memmap_init_zone()` entry, after paging is active, the kernel records the
exclusive PFN range plus node, zone index, and `MEMMAP_EARLY` or
`MEMMAP_HOTPLUG` context in the existing 128-byte record. A `WMAP` signature
at offset `0x74` identifies this interpretation. These four words reuse the
earlier MMU-handoff fields only after the handoff and paging markers have been
recorded; the decoder reports the active zone and explicitly notes that the
handoff words have been replaced.

The existing one-per-512-PFN checkpoint remains enabled. A separately gated
window records the end PFN of each 16-page block in `0x2ebf0..0x2ec2f`, adding
four phase stores if the whole window is visited. The more intrusive detailed
per-page tracing remains disabled. This narrows the observation around the
repeatable checkpoint while keeping the trace record within the already-tested
read boundary.

## Build and offline checks

- The trace profile built successfully with the pinned Android GCC 4.9 toolchain. The combined `zImage-dtb` SHA-256 is `36e336bd343f491a698119fa032fe5bb98579dff061f7682749f5b69c0093b56`; the standalone DTB SHA-256 is `ab186459f800c309124302757b2e883f757d80d3cf8d2314869fa7890fc18949`.
- The trace-disabled early profile also built successfully after guarding the trace call. Both profiles passed the ARM image, appended-DTB, single-CPU, and pre-console checks.
- The compiled `memmap_init_zone()` harness passed 12 cases, including the high-PFN window, zone bounds, hotplug context, and not-ready, bad-cookie, and bad-magic guards. Pageblock update is stubbed; this harness does not emulate real MMU/cache behavior.
- Other offline checks passed: 64 ARM entry snippets; 32 entry-flow runs; 48 MMU mapping runs, five ATAG converter scenarios and two `start_kernel` prologues; four static-map cases; nine fatal-path cases; 30 allocator checkpoints; 23 decoder cases; and the BigPart suite.

## Staged hardware test

The candidate is only a diagnostic kernel-plus-DTB build, not a flashable
Android boot image. The Xoom bootloader rejects RAM boot. Under the user's
existing authorization, a future hardware attempt may write only the boot
partition, first verify the original boot and recovery readbacks, then restore
the exact original boot image and verify both images and Android startup. The
trace should be retrieved once through the bounded read-only reader after
restoration. Recovery, partition layout, and Android data are not part of this
test. A new checkpoint would narrow where execution stopped; it would not by
itself prove a particular fault or fix the boot.
