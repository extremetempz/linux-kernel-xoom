# Combined p9 cache + p10 data Android boot — passed

Image:
`artifacts/storage-final2-ready/wingray-android44-persistent.img`
SHA256 `8da71ed5219108da1164209a68be4295a59761063b931585e0ce2c7e80054f13`.

The final Android boot validated in `android44-persistent` mode:

```text
/dev/mmcblk0p9  /cache ext4 rw
/dev/mmcblk0p10 /data  ext4 rw
/system ext4 ro,noload
p9 0
p10 0
p8/disk 1
exec_original_android_init
SurfaceFlinger running
zygote running
```

The p9 cache write test had already passed separately across two boots. This
boot confirms the same approved p9 cache is mounted read-write alongside the
persistent p10 data while Android runs.

Host validation now accepts an approved p9 cache mount in
`android44-persistent`; a tmpfs cache remains accepted for older Stage C images.
No cache format, Stage D, factory reset or p10/p9 repair occurred.
