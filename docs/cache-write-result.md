# p9 cache write and persistence test — passed

Test image:
`artifacts/cache-test2-ready/wingray-android44-persistent.img`
SHA256 `814cbae80e1a8928d3c77f7969755f5445cdb45964d0316d167a6987dd3672ef`.

The image mounted p9 `/cache` ext4 rw, wrote only
`/cache/xoom-cache-test/persistent-v1.bin` and its boot stamp, synced, and
unmounted. It did not start Android.

First boot:

```text
BOOT_ID 03c68a7d-b3cc-4492-8c56-a4f4f3ea8860
CACHE_UUID 57f8f4bcabf4655fbf67946fc0f9f25b
CACHE_WRITE_OK_REBOOT_REQUIRED
```

Second boot, same image, no reflash:

```text
BOOT_ID 4c428459-e031-4cd0-bd85-34d22094ef54
CACHE_UUID 57f8f4bcabf4655fbf67946fc0f9f25b
CACHE_FILE_PERSISTED_VERIFIED
```

The boot IDs differ and the same-boot guard did not trigger. The fixed 4118-byte
payload survived a full power cycle. p10 was mounted only for the common gate and
was not written; the test files are on p9 `/cache`.

No format, factory reset, cache-p9 repair, Stage D or Android boot occurred in
the test image. The normal combined image remains:

`artifacts/storage-final2-ready/wingray-android44-persistent.img`
SHA256 `8da71ed5219108da1164209a68be4295a59761063b931585e0ce2c7e80054f13`.
