# Stage C persistent Android image — built, not flashed

Built from the current `persistent` profile with the verified post-repair host
evidence and the Stage B two-boot proof.

## Inputs

- Host evidence:
  `/home/justin/xoom-p10-backup-postrepair/host-inspection.json`
- Post-repair backup:
  `05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb`
- Stage B proof:
  `artifacts/stageb-two-boot-proof.json`
  - first boot `ef072250-78b3-4f3c-a1b2-43590cac15e3`
  - second boot `ed60c63c-02c5-46f3-b441-df647bb8a5fc`
  - `TEST_WRITE_OK_REBOOT_REQUIRED` then `TEST_FILE_PERSISTED_VERIFIED`
  - both RC0/unmount0 and p10 RW / p9 RO.

## Image

`artifacts/storage96-stageC-postrepair-ready/wingray-android44-persistent.img`

- 4,222,976 bytes
- SHA256 `15ef5b6e22724c7c0134c23344806ae7f44d4022640c2376c1e1f839a18397a4`
- Kernel SHA256 `106d49d32520afcc36d4d81fbec8eec6f3b0086f32d080b090445ab1e626f900`
- Boot audit passed.
- Under the 8MiB boot limit.
- No flash or tablet write occurred.

## Embedded approval

```text
57f8f4bcabf4655fbf67946fc0f9f25b
1c0000004200000013000000
05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb
```

Fstab:

```text
/dev/block/mmcblk0p8 /system ext4 ro,noload,nosuid,nodev wait
/dev/block/mmcblk0p10 /data ext4 rw,noatime,nosuid,nodev,errors=remount-ro wait
# cache deliberately tmpfs until independent cache verification
```

No cache mount. No `mount_all`.

## Behavior on first boot

This image will:

- verify the approved p10 UUID/features and clean state;
- release p10 only;
- mount p10 `/data` read-write;
- keep p8, p9 and whole disk read-only;
- start the retained Android services.

It is a **Stage C physical-write/Android boot image**. It must not be flashed
without a separate explicit authorization.

## Known limits

- Cache remains unverified and is not mounted; Android cache-dependent behavior
  is untested.
- The fixed Stage B test directory remains in `/data/local/xoom-storage-test`.
- Application/database compatibility is not proven.
- The post-repair backup does not include the Stage B test files.
- The manifest reports `writes_authorized=false` and a conservative
  `userdata_backup_verified=false`; the embedded approval and Stage B proof are
  the build gate.

## Capture mode

The host now accepts `android44-persistent`:

- p1–p9 and whole disk read-only; p10 writable;
- `/data` must be p10 ext4 mounted `rw`;
- `/cache` must be a fresh tmpfs, never p9;
- `/system` must be read-only;
- the Android init execution marker is allowed.

No image rebuild was needed for this host-side validation.

## First Stage C boot

The report validated in `android44-persistent` mode:

- p10 `0`; p8/p9/whole disk `1`;
- `/data` p10 ext4 `rw`;
- `/cache` fresh 96MiB tmpfs, p9 not mounted;
- `/system` ext4 ro,noload;
- read-only `/system/lib/hw` and `/system/lib/egl` overlays;
- Android init executed;
- surfaceflinger and zygote running;
- no Stage D or cache p9 write.

The report did not expose a top-level kernel boot ID, so Android persistence
across reboot still needs a second controlled boot and comparison of existing
userdata state.


## Reboot-tolerant gate — image 60226983

The bootstrap now accepts a p10 superblock that differs from the approved base
only by the ext4 `needs_recovery` incompat bit (0x4). It still requires:

- exact UUID;
- zero recorded error count;
- base compat/incompat/ro-compat features after masking only 0x4;
- state `0100`, or `0000` when and only when recovery is pending.

The normal read-write mount then replays the journal. No full e2fsck, format or
cache-p9 access is performed.

Image:
`artifacts/storage96-stageC-reboot-ready/wingray-android44-persistent.img`

- 4,222,976 bytes
- SHA256 `60226983d438b969fb9157700fc08ec295746d10145cbbf6b13b29b073c8e8d3`
- Approval and fstab unchanged.
- Boot audit passed.
- Not flashed.

This permits repeated forced power cycles after Android shutdown hangs, as long
as the only pending difference is the journal recovery bit.

## Reboot image correction — 183597ba

The first reboot-tolerant gate used the full little-endian incompat word for the
mask, so `0x46` became `0x46000000` and the mask never matched. The corrected
gate uses the first incompat byte:

- `0x46 & ~0x04 == 0x42` (approved base);
- `0x46 & 0x04 == 0x04` (pending recovery).

Image:
`artifacts/storage96-stageC-reboot2-ready/wingray-android44-persistent.img`

- 4,222,976 bytes
- SHA256 `183597ba60580729bfaadfaf642b073a477bb494e3d1b09cd6da2ac629d398da`
- Boot audit passed.
- Approval/fstab unchanged.
- Not flashed.
