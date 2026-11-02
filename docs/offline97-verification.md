# Offline97 verification checkpoint — 3 November 2026

This verifies the committed storage96/offline97 checkpoint. It does not
authorize a tablet flash, physical userdata repair, restore or writable mount.

## Source state

- Project branch: `deepseek`
- Verified project commit: `3fd6b67` (fast-forwarded from
  `codex/persistent-storage96`)
- Kernel patch `0178-wingray-storage-bio-and-backup-readonly.patch` is applied
  to the local donor and committed as `989370f8`. The project test requires the
  `wingray_storage_write_blocked` path and fails without it.
- The offline97 runtime drafts are syntax-checked only.

## Tests rerun

- `tests/test-offline97-tools.py`: passed under Cortex-A9 emulation with the
  standalone checker. Covered clean fsck, counter/bitmap detection,
  conservative preen, recheck, journal-only replay and a write beyond 30 GB.
- `tests/test-storage-host96.py`: 8/8 passed.
- `tests/test-storage-policy96.py`: passed after applying kernel patch 0178.
- `tests/test-storage-write96.py`: passed.
- `tests/test-storage-identity96.py`: passed.
- `tests/test-recovery-storage-preflight.py`: passed; write approval remained
  false.

Checker SHA256:
`b063d57f8bdd3c8474a6ad3ad69faa13dfac3e17d251da50557052b07096d171`,
815912 bytes, static ARMv7, non-NEON. Physical runtime remains unvalidated.

## Evidence not local

The host-repair review records a complete raw p10 backup of
30334779392 bytes with SHA256
`c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579`,
and a repaired host copy with SHA256
`9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f`.

Neither object is present under `/home/justin` in this checkout, and
`/home/justin/xoom-backups` is empty. Those hashes are therefore
operator-supplied evidence and cannot be independently rehashed here. Do not
claim the backup or repaired copy is locally verified.

## Not yet built

No offline97 boot image exists. `diagnostic/offline97-{init,ramtest,report,server}.sh`
are not packaged, linked, boot-audited or hardware-tested.

The safe next build is a read-only RAM runtime with:

- the serial gadget and no mass-storage LUN;
- no Android/TWRP and no physical filesystem mounts;
- immutable p9/p10/whole-disk policy;
- the standalone checker and the two compressed fixtures;
- fixed PING/REPORT framing only.

It must be boot-audited and reviewed before a read-only hardware boot. It cannot
repair userdata.

## Boundary

- No tablet access, flash, mount, repair or restore was performed by this
  verification.
- No StageB/C or persistent Android authorization.
- No cache or userdata modification.
- Physical repair remains blocked until the exact raw backup and repaired copy
  are located and rehashed and a read-only offline97 environment passes hardware
  validation.
