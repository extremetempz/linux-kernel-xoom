# Stage B image using verified post-repair evidence

Built 3 November 2026 with the current storage96 code. No flash or tablet write
occurred.

## Inputs

- Host evidence:
  `/home/justin/xoom-p10-backup-postrepair/host-inspection.json`
- Post-repair p10 backup SHA256:
  `05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb`
- Profile: `persistentwritetest`
- Kernel data-only policy; cache remains tmpfs.

## Image

`artifacts/storage96-stageB-postrepair-ready/wingray-android44-persistent-write-test.img`

- 4,225,024 bytes
- SHA256 `b5208dd55128514d04cf2c35e1e390fede2733de54d24704c800df197a392619`
- Kernel SHA256 `67c73580c9cc1fb873454ffd3587ff0533f84eeb8be76ee7a9c7190978c70b15`
- Boot audit passed.
- Under the 8MiB boot limit.
- Generated fstab:
  - `/dev/block/mmcblk0p8 /system ext4 ro,noload,nosuid,nodev wait`
  - `/dev/block/mmcblk0p10 /data ext4 rw,noatime,nosuid,nodev,errors=remount-ro wait`
  - no `/cache` entry.
- Generated `init.rc` has no `mount_all`.

## Embedded approval

`/bin/storage-data-approved` contains:

```text
57f8f4bcabf4655fbf67946fc0f9f25b
1c0000004200000013000000
05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb
```

This binds the repaired p10 UUID, reviewed feature words and the verified
post-repair backup hash. The policy helper still requires this file before p10
release.

The generated manifest reports `writes_authorized=false` and conservatively
`userdata_backup_verified=false`; the embedded approval is the actual
evidence binding. Flashing still requires explicit operator authorization.

## Stage B behavior

First boot:

- bootstraps system read-only;
- verifies p10 UUID/features/state;
- releases p10 only;
- mounts p10 `/data` read-write;
- writes only `/data/local/xoom-storage-test/persistent-v1.bin`;
- unmounts data;
- holds.

Second boot must verify the existing payload and must not rewrite it.

## Not permitted yet

- Do not flash without explicit authorization.
- Do not mount or write cache.
- Do not boot Android.
- Do not flash Stage C.
- No automatic reboot.

The old Stage B image `1a6b…` remains obsolete.
