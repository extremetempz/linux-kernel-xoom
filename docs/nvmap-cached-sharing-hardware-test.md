# Cached nvmap sharing — hardware attempt 40

24 October 2026. **Initial cacheable CPU-buffer sharing and imported-lifetime
smoke test passed** on the MZ604 P3, using the unchanged allocator-only kernel
from attempt 39. No GPU engines, GART, display takeover or DVFS were enabled.
The uncached test source and all tested kernel profiles remain preserved.

## Implementation and checks

`diagnostic/nvmap-cached-sharing-probe.c` reuses Decatf's actual nvmap ioctl
structures and CREATE/ALLOC/GET_ID/FROM_ID/PARAM/PIN/MMAP/CACHE/FREE interfaces.
Its allocation and both mappings use the donor's `NVMAP_HANDLE_CACHEABLE` value
3; the builder checks that value against the donor header. It never mixes
cached and uncached aliases. Each allocation is 64 KiB in the verified generic
heap only; size, heap, physical bounds, alignment and both clients' pin addresses
are checked before accessing mapped memory.

For each of two cycles:

1. Create and allocate through the owner client; export its ID.
2. Open a second nvmap client, import the ID, pin and map the same buffer.
3. Write through the owner, issue writeback and importer invalidation, and verify
   through the importer. Reverse direction with writeback/invalidate and verify.
   Repeat with a second pattern.
4. Unmap, unpin, free and close the owner client completely.
5. Invalidate/read the imported mapping, write another pattern, maintain cache,
   and verify. Finally unmap, unpin, free and close the importer.

These are **two independent device-open clients in one process**, not a
cross-process or concurrent producer/consumer test. ARM32 static non-NEON build
and image checks pass. The actual probe control flow passes 67 host fixture
success/failure/cleanup cases; fixtures do not model real cache hardware.
The one-shot probe runs separately from the fixed USB reporter with the existing
30-second timeout. No Android block device is mounted or written by the runtime.

## Physical evidence

Boot image SHA-256:
`99265d7128f2ca0307830c4e6453e8a41f55a822739a272284e7ec33703eea46`.
Kernel component, unchanged from attempt 39:
`01b6d6acbde6938597124568f2386d3c4774238e4838f7cb8114434a7d229e7d`.
Probe SHA-256:
`d6bd94b01cc1cb3cf5e2b6659ca5c3f6ea35385363fa31e4c22416c5579103a8`.

Two independently nonce-bound/checksummed reports at about 45 and 51 seconds
uptime contain two `NVMAP_CACHED_TWO_CLIENT_PATTERNS_OK` markers, two
`NVMAP_IMPORTED_MAPPING_SURVIVES_OWNER_CLOSE_OK` markers,
`XOOM_NVMAP_CACHED_SHARING_PASSED cycles=2 bytes=65536 clients=2`, and exit 0.
Both reports observe the **same one-shot execution**, not independent runs.
Both CPUs started; USB, full eMMC capacity and all ten BigPart extents match the
reference. No panic or Oops appears in the captured logs. The prior early sysfs
permission warning remains; this test does not resolve unrelated warnings.

Original boot restoration and complete post-restore boot/recovery partition
hash verification passed. The original Android ROM is boot complete with a
stable boot ID.
Recovery was not written. Raw reports and device identifiers are excluded from
Git. Private artifacts preserve the exact image, probe, transactions and reports.

## What this establishes, and the next graphics gate

This demonstrates the tested cacheable CPU access, maintenance ioctl sequences,
ID sharing and survival after owner release. It does not establish DMA-visible
coherency, cross-CPU/process transfer, arbitrary alias handling, leak freedom,
allocation-pressure endurance, async fences, GPU submission or acceleration.
Successful readback alone cannot prove each cache operation was independently
necessary or correct under every cache state.

The next graphics stage should reuse the existing Decatf host1x/nvhost code and
Motorola submission compatibility patches, with a separate host-only resource
profile. Validate Motorola register/IRQ/clock/reset ownership and syncpoint reads
before engine submissions. Keep the tested allocator profile intact; it
intentionally excludes host/GART drivers. Follow with GART mapping/lifetime
checks, then the already prepared offscreen EGL probe using matched Wingray
libraries/HALs, and only then framebuffer/composition and fence integration.
Samsung regulators, pinmux, timings and power controls remain excluded. No new
GPU driver was invented or enabled in this bounded usage window.
