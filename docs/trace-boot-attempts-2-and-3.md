# Instrumented boot attempts 2 and 3

Reviewed 19 October 2026. Neither attempt established a complete kernel boot or
Android userspace. Both were followed by restoration of the original boot image,
return to working Android, one bounded trace retrieval and byte-for-byte device
readback verification of both boot and recovery against the preserved originals.
Recovery was not flashed and partition layout was not changed.

## Verified hardware progress

| Attempt | Candidate SHA256 | Trace |
|---|---|---|
| 2 | `216616c0e894fb86041d0b970eb6e106e3beed9fd4fb0560da4e17f5de28236e` | Format 1, cookie `0x584d0002` |
| 3 | `b0ce64b12566169a1f46b67d2852a8ffc5e5fd8fc79370e80621c20cb17d2bb7` | Format 2, cookie `0x584d0003` |

Attempt 2 passed CPU-mode setup, ATAG caller return, decompression, main kernel
entry and the marker before MMU enable. The Tegra early-init marker was absent.
The literal-pool correction from attempt 1 therefore allowed substantially later
execution. The retained `/proc/last_kmsg` identifies the legacy 2.6.39.4 kernel;
it is not a 4.4 panic log and must not be used to diagnose a new-kernel exception.

Attempt 3 additionally passed:

- `__mmap_switched` entry with MMU enabled.
- Data/BSS startup and the handoff to C.
- `start_kernel()` and `setup_arch()` entry.
- Device-tree machine selection.
- The last marker immediately before `paging_init()`.

ATAG-to-DTB conversion returned **0** in the corrected format-2 trace. Tegra
`init_early` and the early initcall markers remained absent. This does not prove
the stop is inside `paging_init()`; later setup code and the old early trace
helper remain within the unobserved interval.

Both recorded entry r0=0, r1=`0xa49` (2633/STINGRAY), r2=`0x100`,
CPSR=`0xd3`, SCTLR after mode setup=`0x00c5207a` and MIDR=`0x411fc090`.
The captured SCTLR has MMU disabled, supporting interpretation of the PC-derived
execution base `0x00a00800` as physical at that point. Header addresses remain
declarations, not the observed entry placement.

Attempt 3's MMU handoff captured requested SCTLR=`0x10c53c7d`, boot DTB pointer
`0x00afc098`, TTBR value=`0x4059` (base `0x4000` plus attributes) and virtual
jump=`0xc01be2e0`. The later markers directly demonstrate execution beyond this
handoff; the requested SCTLR field is not itself a readback of final SCTLR.

Neither user confirmation supplied a specific candidate-screen description.
USB gadget is disabled in these diagnostic profiles. Screen appearance and lack
of USB enumeration are not used as execution-stage evidence.

## Restoration and evidence

After each attempt, current device boot and recovery matched the original
images byte-for-byte, respectively:

- `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`
- `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`

Attempt 3 initially lost its VMware USB attachment during restoration preparation.
The product-query timeout occurred before any restoration write. Once the user
reattached fastboot, product verification and original-image restoration both
succeeded. No second candidate flash was performed.

Both trace reads returned stable 128-byte records with remote exit zero. Android
remained in the same boot during retrieval with no new kernel fault markers.
Temporary readers were removed. Raw transport, device identifiers, memory bytes,
logs and image readbacks remain ignored/local under the respective
`artifacts/trace-boot-attempt-*-prepared/` directories, not in GitHub.

## Corrections and next diagnostic build

These source changes are separate from hardware findings and are not claimed
to fix the original peripheral-port failure:

1. Patch `0007`, source `34112d2b`: preserve the real converter return status.
   The old caller overwrote r0 with fallback address `0x100` even when no retry
   occurred. Thus attempt 2's raw value 256 is **not** an ATAG error code. The
   decoder now warns and withholds a return-code interpretation for format 1.
2. Patch `0008`, source `df250162`: map the lower console MiB explicitly in the
   initial page table at `0xdfe00000` for MMU-on assembly/early-C stores. The
   descriptor is privileged RW, execute-never and strongly ordered. Accesses
   remain confined to the 128-byte record. This temporary mapping is not used
   after `paging_init()`; the observed attempt-3 markers validate its initial
   usage on this hardware.
3. Patch `0009`, source `1d7a3df9`: replace the old early marker's dynamic
   `ioremap_nocache()` path. `setup_arch()` invokes machine `init_early` before
   `mm_init()` initializes slab and vmalloc; the dynamic mapping path can call
   `get_vm_area_caller()`/`kzalloc_node()` before their prerequisites. This is a
   real instrumentation timing defect, but the trace does not prove hardware
   reached it or that it is the sole cause of the missing later markers.

Patch 0009 installs one page at virtual `0xfe600000`, physical `0x1fe00000`,
using `iotable_init()` in Wingray's `map_io` path. That API uses early allocation
and registers the static mapping before normal vmalloc initialization. The
address avoids the existing Tegra static IO ranges, vectors, fixmaps and PCI IO
window. The helper uses guarded relaxed IO accesses and DSB, without allocating
or changing mappings during `init_early`.

New phase codes use the existing record's unused word at offset `0x78`. They
bracket paging entry/memory-type setup, static IO installation, later paging
steps, setup_arch stages and Tegra early initialization. A zero phase in attempt
3 is expected because that build did not instrument this field. No old hardware
record is reinterpreted as containing the new phase markers.

The first initial-map markers stop before page-table rebuilding. The static-map
markers start only after their `map_io` provider installs the page. The interval
between those two mapping lifetimes is deliberately not accessed; a stop there
would require a further reviewed observation method.

## Offline validation and candidate 4

The trace build compiles and passes image/profile checks. Compiled Cortex-A9
tests pass 64 isolated trace cases, 32 entry-to-mode cases, 48 descriptor/MMU-on
snippet cases, five converter caller cases, two C-entry prologues, and four
static-map callback cases. The callback test stubs kernel services: it verifies
the exact descriptor, non-overlap with Tegra's existing mappings, Wingray guard,
cookie guard and bounded phase write. It does not execute the real ARM MMU or
`iotable_init()` page-table implementation. Decoder regressions also pass.

The uninstrumented `early` control build is checked separately. No control binary
is claimed byte-identical solely because the runtime trace is disabled.
All nine kernel patches also applied in order to the pinned upstream in an
isolated host directory; all 46 affected paths matched the current donor tree
byte-for-byte. This verifies fresh-series reconstruction without resetting work.

Prepared candidate 4, cookie `0x584d0004`, format 2:

- Kernel/DTB SHA256:
  `24c98b369a079332908f7a4791d7200bed6ed26446e403540468819fba33a14d`.
- Audited boot image SHA256:
  `6322285b76bea3ceb414c266355a1323428fa093e6a3b6ce5044a10750fe29b5`.
- Local image: `artifacts/trace-boot-attempt-4-prepared/wingray-diagnostic.img`.

Candidate 4 has not been flashed or booted. Another boot-partition test requires
explicit approval for that candidate, restoration and trace retrieval.

## Distance from Android

The current verified milestone is early kernel C setup, not userspace. The next
useful milestone is completed kernel initialization and a diagnostic initramfs
console. Interrupts/timers, storage and BigPart operation, power, display, touch,
Wi-Fi and the remaining peripherals still need runtime validation. Android ROM
integration follows stable kernel bring-up and adds its own userspace/vendor
compatibility work. There is no evidence-based calendar estimate yet.
