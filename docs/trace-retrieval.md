# Trace retrieval: reviewed mapping method

**Subsequent status:** the user approved one hardware preflight, which succeeded
on 18 October 2026. See [the preflight results](trace-retrieval-preflight.md).
The proposal below records the review before that test. Reset retention and
retrieval after a 4.4 boot remain untested.

**Later boot-test status:** [the first instrumented boot report](trace-boot-attempt-1.md)
records successful retrieval of the new kernel's entry record after the approved
boot test and original-image restoration. Boot did not complete. Retention is
now observed for that one reset sequence, with the limits described in the report.

**Latest hardware status:** [attempts 2 and 3](trace-boot-attempts-2-and-3.md)
reached main-kernel entry and then early C setup immediately before paging
initialization. Original boot/recovery readbacks were verified after both tests.
The report distinguishes hardware facts from instrumentation defects and describes
the next unbooted candidate.

## Decision

Use a bounded **read-only userspace `mmap2()` snapshot** for the next proposed
preflight on the unchanged working Wingray ROM. It avoids the demonstrated
`/dev/mem read()` bug, needs no kernel module, boot image, recovery change,
repartitioning or physical-memory writes. A local reader and offline tests are
prepared. **It has not been installed or executed on the tablet.**

This is a source-reviewed candidate with a specific reason to expect it to
avoid the prior panic, not a guarantee of fault-free hardware access. Do not
call it hardware validated until a separately approved preflight succeeds.

## Evidence and source identity

Reference: [flar2/xoom-ElementalX](https://github.com/flar2/xoom-ElementalX/tree/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd),
commit `3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd`, dated 2013-12-10
18:49:18 -0500. Its `elementalx_defconfig` names ElementalX-Xoom-2.1. The saved
installed kernel identifies 2.6.39.4-ElementalX-Xoom-2.1+, built that evening.
This is strong provenance, not proof of a byte-identical build or absence of
local patches in the installed binary. The reference checkout is separate from
the existing port; neither kernel tree was reset or replaced.

These reference files are byte-identical to the already pinned Schischu
baseline: `drivers/char/mem.c`, `arch/arm/mm/{mmap,mmu,init}.c`,
`arch/arm/include/asm/io.h`, `drivers/staging/android/ram_console.c` and
`arch/arm/mach-tegra/board-stingray.c`.

Verified from the saved device captures:

- Physical `0x1fe00000..0x1fefffff` is outside System RAM allocations;
  `0x1ff00000..0x1fffffff` belongs to the existing RAM console.
- The board removes the entire 2 MiB hole with `memblock_remove()`.
- Installed config has MMU, FLATMEM, ARM_DMA_MEM_BUFFERABLE and RAM console
  enabled, with STRICT_DEVMEM disabled. The console has Reed-Solomon ECC.
- The failed direct read faulted at `0xdfe00000` in `memcpy`: the normal
  virtual mapping corresponding to the trace physical address was absent.

## Why mapping changes the fault path

In the reference `drivers/char/mem.c:96`, `read_mem()` converts the physical
address using `xlate_dev_mem_ptr()` then copies from that address. ARM defines
this as `__va(p)` in `arch/arm/include/asm/io.h:302`. Bounds validation does not
exclude internal holes. This explains why the previous read reached an unmapped
kernel address instead of returning a clean error. Never use `dd`, `pread`,
`lseek` plus `read`, or BusyBox `devmem` as fallback at this address.

`mmap_mem()` (`drivers/char/mem.c:305`) instead calls `remap_pfn_range()` to
install page table entries for the requested physical page. It does not copy
through `__va()`. The ARM page-protection function at `arch/arm/mm/mmu.c:512`
uses noncached protection when `pfn_valid()` is false. With the captured FLATMEM
configuration, `pfn_valid()` (`arch/arm/mm/init.c:256`) queries
`memblock_is_memory()`, so the removed hole follows that noncached path.
`O_SYNC` is also requested; it is not the reason the removed hole is noncached.

The existing RAM-console driver explicitly maps its adjacent reserved region
with `ioremap()` and saves an ordinary allocated copy for `/proc/last_kmsg`.
That is supporting evidence for explicit mappings of this reserved DRAM, not
a test of the lower trace page or of userspace mapping on the installed binary.

## Prepared reader

Source: `tools/boottrace/mmap-snapshot.c`; build:

```sh
bash scripts/build-trace-reader.sh
bash scripts/setup-trace-tests.sh
python3 tests/test-trace-reader-arm.py artifacts/trace-reader/mmap-snapshot
```

The GCC 4.9 build is a static ARM EABI5 executable without a dynamic linker or
libc. SHA256 of the tested executable:
`f6d45ea6e2b1269094599d9cdfe0ce8b8a55a23d4b6b382b7e44ddc0ff3633eb`.

- Default invocation prints the plan; it opens no device.
- The explicit `--read-reserved-trace` option opens only `/dev/mem`, with
  `O_RDONLY|O_SYNC`. It maps exactly one 4096-byte page with `PROT_READ` and
  `MAP_SHARED`, physical page offset `0x1fe00` (mmap2 uses 4096-byte units).
- It takes two sets of 32 aligned volatile word loads, confined to the first
  128 bytes. It never scans the hole or reads the upper RAM console region.
- It unmaps and closes before writing the copied record to stdout. Unstable
  snapshots and cleanup failures withhold output. Output is exactly 128 bytes
  on success. No argument accepts another address, length or physical write.
- There is no automatic retry or fallback. There is no ADB deployment script.
  The opt-in switch is an execution guard, not a substitute for approval or
  checking that the device is Wingray with the reviewed memory layout.

Nine scenarios passed under Cortex-A9 emulation of the actual ELF: default
plan, success, failed open, failed mmap, failed munmap, failed close, changing
record, short writes/EINTR, and failed stdout. Hooks assert syscall arguments,
no read/pread calls, no writes to the mapped page, exactly 64 bounded word
loads, and output from the copied stack buffer only after cleanup. The emulator
supplies the mapped page; it does not run Linux's MMU implementation or simulate
the memory controller. A bus error can still defeat userspace containment;
SIGBUS handling would not make an invalid physical access safe.

## Controlled preflight, pending approval

1. Keep the working ROM booted. Recheck only ordinary metadata: kernel version,
   config, `/proc/iomem`, board identity and root access. Stop if the lower page
   is assigned to RAM or a device, or differs from the reviewed layout. Verify
   the local reader hash and original image backup hashes. Do not clear or seed
   physical RAM, load a module, reboot, or modify boot/recovery for this check.
2. After explicit approval acknowledging the earlier panic, deploy the reader
   only to a temporary Android data directory. Run its default mode first.
   Then perform **one** opt-in invocation via an unmodified binary ADB stream
   to a new host file. Host capture must refuse overwrite and reject nonzero
   exit status, stderr, truncation, or any output size other than 128 bytes.
   Do not perform a second mapping if the first hangs, faults or disconnects.
3. An invalid trace magic on the working ROM is expected and does not make the
   transport fail: no 4.4 trace was written this turn. Keep transport success
   separate from a valid record. Confirm the old kernel remains responsive and
   inspect ordinary logs for faults. No physical write is needed for this test.
4. Only after that succeeds, design a distinct reset-retention experiment and
   obtain approval for its RAM writes/reboot. Use a unique per-attempt cookie,
   save previous evidence, and identify the exact power-button/reset sequence.
   A hardware reset may discard dirty caches or DRAM; do not assume retention.
5. Only after retrieval and retention are demonstrated, package a separate
   trace boot image and seek explicit boot-partition test approval. Preserve
   and subsequently verify restoration of the original image. The existing
   failed candidate remains unchanged. An absent record cannot prove entry
   never happened: reset or bootloader activity may erase it.

## Alternatives considered

- `/proc/last_kmsg` is already usable for the *legacy* console, but cannot expose
  the current lower trace record. Making 4.4 fabricate its ring would overwrite
  the upper console and requires matching the legacy header, ECC and reset
  behavior. Ramoops uses a different format. Reject this shortcut.
- A built-in recovery exporter using `ioremap()` and an immutable proc copy is
  a fallback if userspace mapping is denied. It requires a separate reviewed
  recovery build and approved boot method; loading an approximately matching
  kernel module is unnecessary risk even with MODVERSIONS disabled.
- Passive external UART removes the post-reset RAM retrieval dependency, but
  requires verified Xoom-specific pads, voltage and physical access. No pinout
  has been established here; do not connect an assumed Tegra UART pinout or an
  RS-232-voltage adapter. This remains a separate hardware investigation.

No tablet commands, physical-memory reads, flashes or reboots were performed
during this source review and reader preparation.
