# Post-repair p10 backup — verified 3 November 2026

## Result

The repaired physical p10 was acquired read-only through the storage96
file-backed gadget.

- image: `/home/justin/xoom-p10-backup-postrepair/userdata-p10.img`
- size: `30334779392` bytes
- SHA256: `05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb`
- UUID: `57f8f4bcabf4655fbf67946fc0f9f25b`
- source RO at acquisition: `1`
- independent second O_DIRECT source read matched
- source and backup e2fsck completed with no warnings
- `DATA_BACKUP_VERIFIED=true`
- `DATA_FILESYSTEM_VERIFIED=true`

The backup directory contains the acquisition, source and backup superblock
logs, both fsck logs, kernel before/after logs, second-read receipt and host
inspection.

This is the first verified post-repair raw image. It is not the pre-repair
acquisition and must not be mixed with it.

## Preserved images

| Purpose | SHA256 |
|---|---|
| original pre-repair p10 | `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579` |
| host-repaired experiment | `9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f` |
| physical repaired p10 backup | `05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb` |

## Boundary

No p10 write occurred during acquisition. The tablet is still running the
read-only backup gadget and must be returned to a define state by power-cycle.

No Android boot, Stage B/C, cache mount or persistent write is authorized by
this backup. The next code review must choose a current write-test image and
confirm its policy gate against this repaired source.
