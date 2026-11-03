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
- `/cache` must be absent;
- `/system` must be read-only;
- the Android init execution marker is allowed.

No image rebuild was needed for this host-side validation.
