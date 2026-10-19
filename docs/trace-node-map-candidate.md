# Node-map and zone diagnostic candidate

Prepared 19 October 2026 from source commit `fc6250cd`. Patch `0011` adds
checkpoints only; it does not correct the still-unproven hardware stop.

Candidate SHA256:
`972e84b4f839d86af09b05e348f5168fb34fb198086a10bac5d2329b312b4812`.
Trace format 2, cookie `0x584d0006`. Matching build retained at
`/tmp/xoom-trace-zones`; private image/evidence at
`artifacts/trace-boot-attempt-6-prepared/`.

Hardware outcome: see [attempt 6](trace-boot-attempt-6.md). The original boot
image was restored and both boot and recovery readbacks verified.

## Checkpoint interpretation

- `0x500`–`0x504`: entry, zone sizes, holes, pre-node call, node call returned.
- `0x510`–`0x515`: node entry, total-page calculation returned, node-map setup
  returned, node-map debug printk returned, deferred-init reset returned,
  zone-core setup returned.
- `0x520`–`0x523`: node-map entry, immediately before allocation, allocation
  returned, node-map pointer stored. An allocation-return marker does not prove
  its pointer is non-null or usable.
- `0x530`: zone-core setup entered.
- `0x600 + (zone_index << 4) + step`: zone entry (1), before per-CPU pageset
  initialization (2), pageset returned (3), before usemap allocation (4), usemap
  returned (5), empty-zone setup and its BUG check passed (6), memmap initialized
  (7). The zone index is the compiled enumeration, not a fixed zone name.

The rolling slot is not a chronological log: use the source's actual call
order, including nested calls. A missing marker bounds an unobserved interval;
it does not by itself prove a particular instruction caused the stop.

## Validation and scope

The trace and trace-disabled early profiles compile and pass profile checks.
The image audit accepts header layout, gzip payload, appended DTB and component
checksums. Existing compiled entry, ATAG, MMU, static-map and fatal-hook tests
pass. Thirty compiled allocator-helper cases check the readiness, magic,
version and cookie guards and bounded phase writes. The trace-disabled binary
has neither the helper nor its readiness state. Fifteen offline decoder cases
pass, including node-map/per-zone records and unknown phases.

Emulation does not execute the real allocator or ARM page-table walker and
cannot establish a hardware boot. No memory-bank size, HIGHMEM setting,
allocator algorithm, partition layout, original image or recovery image was
changed. The standing authorization covers a boot-partition test followed by
original restoration, one bounded trace retrieval and readback verification.
