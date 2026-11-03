# Offline98 p10 repair result — 3 November 2026

## Authorization and execution

The operator explicitly authorized the interactive p10 repair. The environment
released p10 only; p9, p8 and the whole disk remained read-only throughout.

e2fsck 1.47.0 recovered the journal and repaired the previously identified
orphan/free-count/inode-bitmap state. Two optional extent-tree optimizations
were accepted; other optional optimizations were declined.

Final interactive result:

```text
Free blocks count wrong (6805365, counted=6805493). Fix<y>? yes
Free inodes count wrong (1827360, counted=1827448). Fix<y>? yes
Padding at end of inode bitmap is not set. Fix<y>? yes
/dev/mmcblk0p10: ***** FILE SYSTEM WAS MODIFIED *****
/dev/mmcblk0p10: 16712/1844160 files (9.6% non-contiguous), 600075/7405568 blocks
XOOM_REPAIR_E2FSCK_EXIT 1
```

A missing BusyBox `sync` path was reported immediately after e2fsck. The tablet
was left powered for writeback before being power-cycled. The repair script has
since been corrected to use `/bin/busybox grep` and `/bin/busybox sync`.

## Post-repair read-only fsck

The validation-only PREFLIGHT path was rerun with p10 read-only and no release:

```text
Pass 1: Checking inodes, blocks, and sizes
Pass 2: Checking directory structure
Pass 3: Checking directory connectivity
Pass 4: Checking reference counts
Pass 5: Checking group summary information
/dev/mmcblk0p10: 16712/1844160 files (9.6% non-contiguous), 600075/7405568 blocks
XOOM_REPAIR_PREFLIGHT_END
```

No orphan, free-count, inode-bitmap, directory or I/O warnings appeared. This is
a complete read-only fsck result for the physical p10.

## Post-repair read-only inspection

The inspect image reported:

- p10 read-only `1`; whole disk and p8/p9 read-only `1`;
- ext4 magic `53ef`;
- crypto footer absent;
- read-only mount succeeded;
- `/data` layout preserved;
- `/data/local/xoom-storage-test` removed;
- feature incompat changed from `70` to `42`, consistent with recovery cleared.

The Android userspace e2fsck still crashes with 139, so the standalone
environment remains the only valid fsck evidence.

## Preserved evidence

- Original pre-repair p10 backup:
  `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579`
- Host-repaired experiment:
  `9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f`
- The physical p10 has now been repaired and passes a complete read-only fsck,
  but a new post-repair raw backup has **not** been acquired or verified.
- `XOOM_REPAIR_E2FSCK_EXIT 1` means corrected errors, not a fully clean original
  state; the subsequent read-only fsck is the health proof.

## Gate

No Android boot, Stage B/C, cache mount or persistent write has occurred. Do not
treat the pre-repair backup as a backup of the repaired p10. Acquire and verify a
fresh post-repair p10 image before any controlled write test.
