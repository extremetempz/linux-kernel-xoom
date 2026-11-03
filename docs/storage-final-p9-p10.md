# Combined p9 cache and p10 data image — 3 November 2026

Built from `codex/shutdown-cache` at the merged p10 Stage C reboot fixes.

## Evidence

- p10 post-repair host evidence:
  `/home/justin/xoom-p10-backup-postrepair/host-inspection.json`
  backup `05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb`
- Stage B two-boot proof:
  `/home/justin/linux-kernel-xoom/artifacts/stageb-two-boot-proof.json`
- p9 post-repair host evidence:
  `/home/justin/xoom-p9-backup-postrepair99/host-inspection.json`
  backup `09b94b39fb08e3c1db8d5fa1c63949185b8dc08f99c265047e9f263c184001a1`

## Image

`artifacts/storage-final2-ready/wingray-android44-persistent.img`

- 4,229,120 bytes
- SHA256 `8da71ed5219108da1164209a68be4295a59761063b931585e0ce2c7e80054f13`
- Boot audit passed.
- Built locally; not flashed.

## Enabled storage

```text
/dev/block/mmcblk0p8  /system ext4 ro,noload,nosuid,nodev wait
/dev/block/mmcblk0p10 /data   ext4 rw,noatime,nosuid,nodev,errors=remount-ro wait
/dev/block/mmcblk0p9  /cache  ext4 rw,noatime,nosuid,nodev,errors=remount-ro wait
```

Data approval is bound to `05f86fda…`; cache approval is independently bound
to `09b94b39…`. Both tokens require the repaired UUID and reviewed features.

## Additional gates

- p10 journal-recovery tolerance (`needs_recovery` bit only).
- p9 identity/health verification before release.
- clean-shutdown `persistentshutdown` profile.
- p8, boot/recovery and whole disk remain read-only.

No flash, p9 mount or Android boot occurred during the build.
