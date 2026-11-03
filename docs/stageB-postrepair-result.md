# Stage B two-boot persistence result — 3 November 2026

Image:
`artifacts/storage96-stageB-postrepair-ready/wingray-android44-persistent-write-test.img`
SHA256 `b5208dd55128514d04cf2c35e1e390fede2733de54d24704c800df197a392619`.

The image embedded the repaired p10 UUID/features and verified post-repair backup
hash `05f86fda…`. Only p10 was released; p9, p8 and the whole disk stayed RO.

## First boot

```text
BOOT_ID ef072250-78b3-4f3c-a1b2-43590cac15e3
DATA_FILESYSTEM_UUID 57f8f4bcabf4655fbf67946fc0f9f25b
TEST_WRITE_OK_REBOOT_REQUIRED
XOOM_STORAGE_WRITE_TEST_RC 0
XOOM_STORAGE_WRITE_TEST_UNMOUNT_RC 0
```

`/data` was unmounted cleanly.

## Second boot, same image, no reflash

```text
BOOT_ID ed60c63c-02c5-46f3-b441-df647bb8a5fc
TEST_FILE_PERSISTED_VERIFIED
XOOM_STORAGE_WRITE_TEST_RC 0
XOOM_STORAGE_WRITE_TEST_UNMOUNT_RC 0
```

The boot IDs differ and the same-boot guard did not trigger. The fixed file and
stamp survived a full reboot. This proves the controlled two-boot persistence
test only, not Android boot or application compatibility.

## Host parser corrections

- The write-test report contains an outer and inner write-test section; the host
  reader now uses the first BEGIN through the last END.
- The Stage B mode permits unmounted `/data` and no `/cache` after a clean test.
- The old RC 1 report still correctly fails.

## Boundary

No Android boot, Stage C, cache mount or persistent Android write occurred.
No automatic reboot. Stage C still needs a separately reviewed build and
approval; do not treat Stage B as Android persistence approval.
