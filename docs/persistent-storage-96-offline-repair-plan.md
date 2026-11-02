# BigPart offline userdata repair: prepared procedure, not executed

3 November2026. Companion evidence: [host review](persistent-storage-96-host-repair-review.md).
No tablet repair/restore/reboot/flash is authorized or performed by these tools.
The operator requested preparation of an offline repair path and publication.
Approval of this document is not a command to make a physical write.

## Preserved recovery audit

The preserved12MiB recovery image still hashes to
`5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.
Offline parsing identifies Omni Wingray Android4.4.4 recovery, TWRP fstab,
an automatically started `/sbin/recovery` service and `/sbin/adbd`.
Its fstab uses userdata through `sdhci-tegra.3/by-name/userdata` with a
16384-byte footer reservation. This does not prove live BigPart enumeration.

Embedded e2fsck SHA256:
`f38080e72cc8119aee01321c7bf68bd0dd6aa8a6606ad00e072cca9c474cbf9a`.
Embedded tune2fs SHA256:
`d1d8ed1f87f1c9ad598c3125d944a2f37e6ad3a99ec1732eb3d3e7f3e01ecdeb`.
Both are ARM ELF binaries requiring `/sbin/linker`, not standalone static tools.
Neither was executed/validated. Do not conflate them with the ROM tools that
previously failed, or assume they also fail. Their runtime reliability is unknown.
TWRP automatic mounting, journal replay and logging behaviour are also unverified.
**Do not boot this recovery as a supposedly read-only inspection step yet.**

## Current boundary

Image96 exports p10 read-only at both kernel and gadget layers. It cannot repair
userdata and must not be made writable with a host `blockdev --setrw` workaround.
The host's `e2fsck` cannot modify a read-only exported LUN. Do not weaken the known
backup image or change its safety tests to obtain a writable path.

A usable physical repair environment must be reviewed/built separately: it must
start without Android, automatic mounts, filesystem repair, writes to cache or
automatic reboot. It must leave p10 protected until an explicit operator action,
provide an independently usable diagnostic channel and permit an orderly return
to read-only after repair. A dedicated build based on the tested RAM diagnostic
is preferable if existing recovery behaviour cannot be established. Such an image
has **not** been built or hardware-validated in this step. No safe live writable
environment has yet been established; this remains the blocker, not filesystem
compatibility of the clean host copy. No new kernel storage architecture is needed.

## Ordered operator-controlled sequence

1. Retain all three independent host files: original verified acquisition,
   journal-replayed intermediate and clean repaired experiment. Preserve receipts,
   manual repair transcript and both boot/recovery backups. Check host storage and
   backup hashes before authorizing a write. Do not use the repaired copy to
   overwrite the verified original backup or its original health verdict.
2. Review the proposed repair environment, its source, binary provenance, startup
   mounts and repair-tool dependencies. Resolve automatic mounting **before boot**;
   checking mounts after automatic journal replay is too late. Select a verified
   e2fsck version supporting this filesystem. Validate it on disposable copies in
   its actual runtime, not merely by reading an ELF header. If using host e2fsck
   through a purpose-built writable LUN, require automount disabled, one p10-only
   LUN, fixed capacity and explicit write release; never expose the whole disk.
3. Obtain explicit authorization for the exact environment's boot/deployment and,
   separately, the userdata repair. Confirm physical recovery buttons, sufficient
   power and a usable host diagnostic connection. Never flash recovery, repartition,
   format, change charging limits, enable LP2 or boot Android during this sequence.
4. Before any repair, collect live metadata from the selected offline environment:

   ```sh
   python3 scripts/recovery-storage-preflight.py \
     --serial RECOVERY_ADB_SERIAL \
     --output-dir artifacts/storage96-recovery-preflight-new
   ```

   This is only for an environment whose startup behaviour has already been
   reviewed. It performs fixed metadata reads, never unmount, fsck, remount, reboot
   or flash. It records root recovery identity, disk/ten-partition geometry,
   userdata alias, mounts, swap, holders and policy. It always reports physical
   writes unauthorized and environment approval false, even when metadata passes.
   A passing report does not replace tool validation or operator approval.
5. Require disk62521344 sectors; all ten extents must match the tested BigPart
   view below. Require p10 major:minor179:10, alias to mmcblk0p10, start3264512,
   size59247616 sectors and30334779392 bytes. Refuse legacy offsets, a whole-disk
   target, unknown aliases, device-mapper layers, holders, swap, existing filesystem
   users or any eMMC mount. Never repair while Android, a recovery UI or another
   process can mount the same data. A stopped/mounted volume is not proof that no
   process still has raw descriptors; review the environment's processes too.
6. While still protected and unmounted, compare the actual source with the saved
   original acquisition, including UUID, superblock/features, capacity and a full
   source hash. Expected original SHA256 is
   `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579`.
   If anything changed since acquisition, stop; the prior repair rehearsal no
   longer exactly describes the current source. Acquire fresh preservation
   evidence rather than forcing the old verdict.
7. Only with all checks passed and explicit physical-write authorization, release
   p10 alone. Keep p8/p9/whole-disk aliases protected. First journal-only recovery,
   then a complete non-modifying check, following the host rehearsal. If remaining
   errors match the rehearsal, review individual manual repair prompts. Do not
   use `-y`, automated stdin answers, a modifying fsck at boot, or a new repair
   proposal without review. Any I/O error, new inconsistency or tool crash stops
   the operation and preserves diagnostics. Capture complete output/status.
   No executable physical-write command is included here because the environment
   and repair binary have not passed the preceding gates.
8. After an approved repair, flush using the validated tool/environment's normal
   completion path, re-establish read-only policy and verify it. Require a fresh
   complete read-only fsck with exit0, no needs_recovery/error flags, and matching
   UUID/bounds. Record hashes and full repair evidence. Do not automatically boot
   Android. A failed repair must not trigger an automatic restore or retry.
9. Update readiness only with evidence for the **physical repaired source**.
   The existing original report stays blocked and preserved. The host experiment
   is not substituted for it. If the current readiness schema requires a matching
   clean-source backup, create that separately or add a reviewed, evidence-bound
   repair-history extension; never change JSON booleans to bypass the gate.
10. Only afterward prepare the separate approved two-boot fixed-file test; cache
    stays tmpfs until independently verified, automatic LP2 remains disabled.
    Android persistent-data boot follows that test, not the repair itself.

| Partition | Start (512-byte sectors) | Sectors |
|---|---:|---:|
| p1 |51200|6144|
| p2 |57344|4096|
| p3 |61440|4096|
| p4 |65536|8192|
| p5 |73728|4096|
| p6 |77824|24576|
| p7 |102400|16384|
| p8 |118784|2097152|
| p9 |2215936|1048576|
| p10 |3264512|59247616|

## Failure and rollback

No rollback is needed for this preparation: no device changes occurred. Any
later boot-only restore requires the preserved original boot SHA256
`64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
Restoring boot does not undo userdata changes. Raw userdata restore requires
separate approval, a verified matching BigPart writable offline environment,
unmounted p10, full image/source checks, checked write completion and complete
destination readback hash. Never use an unverified fastboot userdata mapping or
restore the repaired experiment merely because fsck passes. Preserve the original
backup and repair evidence even after a successful future recovery.
