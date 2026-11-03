# Offline97 verification checkpoint — 3 November 2026

This verifies the committed storage96/offline97 work and the locally present
host evidence. No physical repair, restore or writable mount was performed.

## Host evidence rehashed locally

- Raw p10 image: `/home/justin/xoom-p10-backup96/userdata-p10.img`
  - size: 30334779392 bytes
  - SHA256: `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579`
  - acquisition and independent second read agree; both records report RO1.
- Repaired host experiment:
  `/home/justin/xoom-p10-preen96-2y07el_a/userdata-repair-experiment.img`
  - size: 30334779392 bytes
  - SHA256: `9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f`
  - read-only e2fsck returned 0 with all five passes and no unresolved-output
    warning.
- `scripts/persistent-readiness.py` rehashed the backup and confirmed:
  - `DATA_BACKUP_VERIFIED=true`
  - `DATA_FILESYSTEM_VERIFIED=false` for the original source
  - `DATA_WRITE_POLICY_VERIFIED=true`
  - `writes_allowed=false`

The original tablet filesystem remains blocked by its source fsck and
`needs_recovery` feature. The repaired image is a host experiment only. The
tablet has not been repaired.

## Tests

- `test-offline97-tools.py`: passed under Cortex-A9 emulation.
- `test-storage-host96.py`: 8/8 passed.
- `test-storage-policy96.py`: passed after applying kernel patch 0178.
- `test-storage-write96.py`: passed.
- `test-storage-identity96.py`: passed.
- `test-recovery-storage-preflight.py`: passed; approval remained false.

Standalone checker:
`b063d57f8bdd3c8474a6ad3ad69faa13dfac3e17d251da50557052b07096d171`,
815912 bytes, static ARMv7 non-NEON. Physical runtime is still unvalidated.

## Read-only offline97 image built

`artifacts/offline97-readonly-ready/wingray-offline97-readonly.img`

- 3,956,736 bytes
- SHA256 `fd3af657cbff3f4efc153e5c95329645e8f848d8ee72ed908301f6a2b354578c`
- Built from the tested inspect kernel/DTB plus a new minimal RAM initramfs.
- Contains the standalone checker and the two compressed fixtures.
- PID1 is `offline97-init`; no Android, TWRP, mass storage, cache, p9/p10 mount
  or physical repair command.
- Serial gadget is enabled; only fixed PING/REPORT framing is exposed.
- RAM test requires the whole disk and all ten BigPart partitions to remain RO,
  then checks the checker on RAM fixtures only.
- Fits below the 8MiB boot limit.

Host mode `offline97` validates the framed report. Hardware boots exposed
ETXTBSY on `/bin/e2fsck`, then a corrupt `/run/e2fsck` copy (SHA256
`0139774e…` instead of `b063d57f…`) when using BusyBox `cp`. The current image
uses `dd` to copy the checker to `/run`, verifies its exact SHA256 before
execution, starts the serial reporter before the copy, records copy failures in
`offline97-state`, and wraps the report in the fixed `XOOM_FRESH_REPORT_V2`
framing. The image is rebuilt but still **not hardware-tested**.

## Boundary

- No flash, tablet write, physical repair or restore occurred.
- No StageB/C, Android persistent boot or cache change.
- The read-only offline97 image may be reviewed and optionally booted only after
  explicit operator approval; it must not be given a writable part.
- Physical repair requires a separate review and authorization after this image
  proves the checker and policy behavior on hardware.


## Hardware result — 3 November 2026

The internal-initramfs image booted on the Wingray and passed the read-only RAM
suite:

- all 13 checker chunks and the embedded manifest matched;
- `/run/e2fsck` final SHA256
  `b063d57f8bdd3c8474a6ad3ad69faa13dfac3e17d251da50557052b07096d171`;
- `e2fsck 1.47.0`;
- clean fixture exit 0;
- corrupted counter/bitmap fixture exit 4;
- conservative preen exit 1;
- recheck exit 0;
- `OFFLINE97_RAMTEST_PASSED_PHYSICAL_WRITES_DISABLED`;
- `RAMTEST_EXIT 0`;
- capture state `offline97_ramtest_passed`.

Report capture:
`artifacts/offline97-hw8/report-private.txt`
(SHA256 `a33fdde2631514ee8bca9d0fa63c4f9088bd4c8ccc8fb7318d97aaa9346f6812`).

No p9/p10 mount, physical fsck, repair, restore or writable operation occurred.
The tablet userdata remains the original unmodified source. The physical repair
environment has not been designed or built yet.
