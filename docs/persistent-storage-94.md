# Concurrent persistent storage bring-up — 1 November 2026

This is a storage integration candidate, not a new ROM. It preserves the
existing Android 4.4.4 system, graphics, Wi-Fi/Bluetooth, CPCAP/LP2 code and
BigPart geometry.

## Status and authorization

- **No persistent write has been authorized or attempted.**
- **No verified off-device userdata backup exists in this workspace.**
- Stage A (read-only inspection) is safe to run before a backup.
- Stage B (write test) and Stage C (Android persistent boot) must not be
  flashed until a verified, restorable backup of `mmcblk0p10` exists.

## A. Existing storage assessment

The original Android fstab extracted read-only from
`artifacts/hardware-private/backup-boot.img` is:

```text
/system   p8   ext4  ro
/pds      p?   ext4  ro
/cache    p9   ext4  noatime,nosuid,nodev,nomblk_io_submit,errors=panic
/data     p10  ext4  noatime,nosuid,nodev,nomblk_io_submit,errors=panic,encryptable=footer
/misc, /boot, /recovery emmc
```

This does not prove the actual on-disk types. Stage A must verify ext4 magic,
features, encryption footer, health and mountability.

BigPart geometry, in 512-byte sectors, is unchanged:

| partition | start | size |
|---|---:|---:|
| p8 system | 118784 | 2097152 |
| p9 cache | 2215936 | 1048576 |
| p10 userdata | 3264512 | 59247616 |

Whole disk: 62,521,344 sectors. The GPT is not modified.

The current working images use:

```text
/system  persistent ext4 ro,noload,nosuid,nodev
/data    tmpfs 256 MiB
/cache   tmpfs 96 MiB
```

The whole eMMC is currently read-only through
`motorola,xoom-firstboot-ro` inherited by the working DTs. The MMC driver sets
`md->read_only`, rejects raw MMC ioctls and prevents `BLKROSET` from clearing
that policy. That whole-device policy is retained for every existing
diagnostic image.

## B. Kernel changes

New Kconfig symbol: `MOTOROLA_WINGRAY_PERSISTENT_STORAGE`.

New property on the eMMC controller:
`motorola,xoom-persistent-storage`.

The persistent DTS deletes `motorola,xoom-firstboot-ro` and adds the persistent
property. The MMC driver then:

- keeps the whole disk (part0) read-only;
- starts every partition read-only (`set_disk_ro(...,1)`);
- permits only partition 9 and 10 to be changed with `BLKROSET(0)`;
- rejects raw `MMC_IOC_CMD`/`MMC_IOC_MULTI_CMD`;
- rejects `BLKPG`/`BLKRRPART`;
- rejects NULL `BLKROSET` with `EROFS`;
- enforces partition read-only policy in `mmc_blk_open()`;
- forces `force_ro` to stay read-only.

The generic block layer also rejects `BLKPG` and partition-table rereads on a
read-only whole disk, so the protection is not dependent on the driver ioctl
entry point alone.

A fixed static helper (`bin/storage-policy`) opens only `/dev/mmcblk0p9` and
`/dev/mmcblk0p10`, verifies the persistent DT marker, refuses inspection mode,
and performs `BLKROSET(0)` plus `BLKROGET`. It cannot write media.

The diagnostic firstboot profiles are unchanged.

## C. Android bootstrap

Normal persistent profile:

1. Verifies board, disk size and all ten BigPart extents.
2. Runs the original pre-init ABI/protection probe while p9/p10 are still RO.
3. Mounts `/system` ext4 `ro,noload,nosuid,nodev` and verifies the system hash
   list.
4. Inspects the 16 KiB tail of p9/p10 for the Android crypto footer.
5. Reads ext4 magic for p9/p10.
6. Refuses encrypted/non-ext4 media before changing a policy.
7. Runs the fixed policy helper; checks p9/p10 `ro=0`, p8 and whole disk `ro=1`.
8. Mounts p10 at `/data` and p9 at `/cache` with the original writable options
   (`rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic`).
9. Starts the existing GPU/Wi-Fi/Android path.

No tmpfs fallback exists in the persistent branch. A mount failure is fatal.
No mkfs, mke2fs, wipefs, mkpart, sgdisk, parted, fsck write or recursive
chown/chmod exists in the runtime.

Read-only inspection mode stops after `/system`, performs no policy change and
never launches Android. Controlled write-test mode mounts only `/data` after
the same checks and writes only its dedicated test directory.

## D. Android init and fstab

The generated persistent fstab is:

```text
/dev/block/mmcblk0p8  /system ext4 ro,noload,nosuid,nodev wait
/dev/block/mmcblk0p10 /data   ext4 rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic wait
/dev/block/mmcblk0p9  /cache  ext4 rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic wait
```

The bootstrap mounts them before Android. The generated `init.rc` has no
`mount_all`, so init does not mount a second filesystem over `/data` or
`/cache`. Existing top-level ownership actions and
`restorecon_recursive /data` remain the ROM's original behavior; there is no
recursive ownership change by this work.

The original Android 4.4.4 startup path, HAL RAM overlays, BCM4329 firmware
overlay, Wi-Fi service and `/data/misc/wifi` credential preservation are
retained. `wpa_supplicant.conf` is created only when absent.

## E. Filesystem safety

- Existing p9/p10 are never formatted, wiped or repartitioned.
- Stage A uses only `dd` reads, `e2fsck -n`, and `mount -o ro,noload`.
- `e2fsck -n` is read-only and never replays the journal.
- Stage B creates only `/data/local/xoom-storage-test/persistent-v1.bin`.
- The test file is created with `set -C` (no overwrite), 4120 bytes, mode 0600,
  owner root, and a fixed SHA-256 payload.
- The second boot verifies the file and never rewrites it.
- No test touches `/data/system`, `/data/app`, `/data/data` or `/data/media`.

## F. Images

### Stage A — read-only inspection

`artifacts/android44-persistent94-inspect-ready/wingray-android44-persistent-inspect.img`

- 4,222,976 bytes
- SHA-256 `5e1355ea84ea9d3dd44a29225c56e15241a95e52fca63d4da43011406d170756`
- Never clears p9/p10, never mounts them rw, never starts Android.
- Safe before a userdata backup.

### Stage B — controlled persistent-file test

`artifacts/android44-persistent94-write-test-ready/wingray-android44-persistent-write-test.img`

- 4,225,024 bytes
- SHA-256 `e398c3ae30ed0c8e1ffa72e3dba5f8bddfc30637b83da9357a6d424ed2059baa`
- **Do not flash until a verified userdata backup exists.**
- First boot writes the fixed file; second boot verifies it; no auto reboot.

### Stage C — persistent Android

`artifacts/android44-persistent94-ready/wingray-android44-persistent.img`

- 4,225,024 bytes
- SHA-256 `62786ae0b6eadaf1fee4b57f09624c124a17eb25babead98aeb1abcbfe11d7a1`
- **Do not flash until Stage A and Stage B pass and a verified backup exists.**

Each ready directory also contains `kernel.config`, `System.map`,
`zImage-dtb`, the persistent DTBs, `runtime-source.cpio`,
`builtin-initramfs.cpio.xz`, `generated/fstab.stingray`, generated init
scripts, `boot-audit.json`, `manifest.json` and `SHA256SUMS`.

## G. Offline validation

Passed source/offline gates:

- persistent-storage tests: 36 checks (geometry, policy, fail-closed behavior,
  no format/repartition/wipe, fstab, GPU/Wi-Fi/LP2 preservation);
- storage profile source gates;
- LP2/PM source gates;
- ARM kernel build, static helper build, ramdisk packing;
- boot-image header audit and deterministic repack (same SHA-256);
- image size below the 8 MiB boot partition;
- generated DTBs contain the intended persistent/inspection/write-test markers
  and no firstboot marker.

Physical filesystem health is not yet validated; Stage A must run on hardware.

## H. Hardware procedures

### Stage A — read-only inspection

1. Confirm original boot/recovery hashes.
2. Flash only:
   `artifacts/android44-persistent94-inspect-ready/wingray-android44-persistent-inspect.img`.
3. Wait for display pattern and USB. The inspector may take up to a few
   minutes for `e2fsck -n`.
4. Capture:

```sh
sudo setfacl -m u:justin:rw /dev/ttyACM0
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/storage-inspect1 \
  --storage-mode android44-readonly
```

5. Read `XOOM_ANDROID44_STORAGE_INSPECT_BEGIN` through
   `XOOM_STORAGE_INSPECT_END` in `report-private.txt`. Parse it offline with:

```sh
python3 scripts/parse-storage-inspection.py   --report artifacts/storage-inspect1/report-private.txt   --output artifacts/storage-inspect1/inspection.json
```

6. Require ext4 magic `53ef`, no crypto footer (unless you intentionally use
   Android encryption), readable superblock, e2fsck result understood, and
   `RO_MOUNT_OK`. Store full report off-device.
7. No Android is started; no policy is changed. Power-cycle to leave.

### Backup gate

**Not satisfied in this workspace.** Before Stage B, produce a restorable
off-device raw image of p10 (and p9 if desired), record its SHA-256, and verify
the backup by reading it back. A boot-image backup is not sufficient.
No private userdata image may be committed to GitHub. See [backup gate](persistent-storage-backup.md).

After both exist, the host-only readiness gate can be evaluated:

```sh
python3 scripts/persistent-readiness.py   --inspection artifacts/storage-inspect1/inspection.json   --backup /path/to/verified-userdata-p10.img   --backup-sha256 <sha256>   --output artifacts/storage-inspect1/write-readiness.json
```

`writes_allowed=true` is a prerequisite, not automatic authorization. It
does not flash or write anything.

### Stage B — controlled write test (after backup only)

1. Flash only the write-test image.
2. Capture report; expect `TEST_FILE_WRITTEN size=4120 sha256=4f5a76d9…` and
   `TEST_WRITE_OK_REBOOT_REQUIRED`.
3. Power-cycle once under operator control.
4. Capture report; expect `TEST_FILE_PERSISTED_VERIFIED`.
5. Do not rerun or delete the file automatically.

### Stage C — Android persistence (after A+B)

1. Flash the persistent image.
2. Verify Android completes startup, GPU/touch, Wi-Fi, Bluetooth, battery,
   power button.
3. Install one small test app and change one harmless setting.
4. Reboot normally; verify the app, setting, Wi-Fi credentials and same user
   environment survive.
5. Verify `/data/media` persists.
6. Only then separately test LP2; do not run LP2 during initial storage
   validation.

## I. Recovery and rollback

- Original boot: `artifacts/hardware-private/backup-boot.img`
  SHA-256 `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Original recovery: `artifacts/hardware-private/backup-recovery.img`
  SHA-256 `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.
- Latest validated LP2 image: `artifacts/lp2g-ready/wingray-android44-gpu.img`
  SHA-256 `cefb6d82198bb9b516bd01be6b3a815331c541c6c419cf6fb4f7a1a842d52b6e`.
- Test 5 image: `artifacts/display80fbtest5-ready/wingray-android44-gpu.img`
  SHA-256 `02ab70c2…`.

Restoring boot does not undo writes already made to `/data`. To restore
userdata, use only the verified raw backup with an operator-approved, offline
write method. Do not format, repartition or factory reset. Do not flash
recovery as part of this procedure.

If Stage A/B/C fails, preserve the report and stop. Do not retry persistent
writes automatically.
