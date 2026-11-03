# Project state — 3 November 2026

## Physical storage

- The tablet is a Motorola Xoom MZ604/Wingray, BigPart layout.
- Physical p10 was repaired with the explicit offline98 p10-only gate.
- p10 was released only for that repair; p9, p8 and the whole disk remained RO.
- Interactive e2fsck fixed the orphan/free-count/inode-bitmap state.
- `XOOM_REPAIR_E2FSCK_EXIT 1` means corrected errors.
- A subsequent complete read-only `e2fsck -f -n` passed all five passes with no
  warnings.
- The tablet was power-cycled and p10 returned read-only.
- Post-repair inspection: ext4, no crypto footer, read-only mount, `/data`
  layout preserved, `/data/local/xoom-storage-test` gone.
- The Android userspace e2fsck still crashes with 139; the standalone checker
  is the valid fsck evidence.

## Verified images

| Purpose | Size | SHA-256 |
|---|---:|---|
| pre-repair p10 backup | 30334779392 | `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579` |
| host-repaired experiment | 30334779392 | `9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f` |
| post-repair p10 backup | 30334779392 | `05f86fdad2edb4d34a57481282813bf825dee0b560c279e4113d77a79565b8fb` |
| validated offline97 RO image | 3956736 | `fd3af657cbff3f4efc153e5c95329645e8f848d8ee72ed908301f6a2b354578c` |
| offline98 p10 repair image | 3956736 | `efd7163e4452ab32477e13775ff2af4aa04769f59de10164a64b2a92c28d0874` |
| storage96 RO mass backup image | 4231168 | `72717d7d7de316bba4bbbdc910b5668397d7a9b6e4b6aff275c43f2b1549fbac` |
| LP2 rollback | 4225024 | `cefb6d82198bb9b516bd01be6b3a815331c541c6c419cf6fb4f7a1a842d52b6e` |

Post-repair p10 UUID: `57f8f4bc-abf4-655f-bf67-946fc0f9f25b`.
Post-repair backup is verified by two independent source reads and clean host
fsck. It is the only valid backup of the repaired p10.

## Offline tooling

- Standalone static ARMv7 non-NEON e2fsck 1.47.0:
  `b063d57f8bdd3c8474a6ad3ad69faa13dfac3e17d251da50557052b07096d171`
- Hardware RAM validation passed:
  - clean fsck exit 0;
  - counter/bitmap detection exit 4;
  - conservative preen exit 1;
  - recheck exit 0.
- Checker delivered through a kernel-internal initramfs; external ramdisk
  truncation was the cause of earlier corrupt files.
- Physical execution of the checker is now proven; this is not proof of
  application/database integrity.

## Current gate

No Android boot, Stage B/C, cache mount or persistent write has occurred.

Stage B must be rebuilt from the current storage96 code with the verified
post-repair host evidence embedded:

`/home/justin/xoom-p10-backup-postrepair/host-inspection.json`

The old Stage B image `1a6b…` is obsolete and must not be flashed. The next
sequence is:

1. build current write-test image with `XOOM_STORAGE_HOST_EVIDENCE`;
2. review embedded UUID/features/backup hash;
3. flash Stage B only after review;
4. two-boot fixed-file persistence test;
5. only then consider Android persistent boot;
6. cache remains tmpfs until separately verified.

The post-repair backup is complete, so Stage B is unblocked, but no new write
tests have been performed.

## Safety

- Do not use the pre-repair backup as a backup of repaired p10.
- Do not restore the host-repaired experiment to the tablet.
- Do not boot Android or Stage C yet.
- Do not expose whole disk, p8 or p9 writable.
- No physical write is currently in progress.

## Repository

- Branch: `deepseek`
- Last repair/evidence commit before this state file: `fea3b7b`
- Host-repair result: `docs/offline98-repair-result.md`
- Post-repair backup: `docs/p10-postrepair-backup.md`
- Offline97 validation: `docs/offline97-verification.md`
- Repair procedure: `docs/offline98-repair.md`


## Stage B/C update — 3 November 2026

- Stage B two-boot fixed-file persistence passed on hardware.
- Stage C image built with post-repair host evidence and Stage B proof:
  4,222,976 bytes, SHA256
  `15ef5b6e22724c7c0134c23344806ae7f44d4022640c2376c1e1f839a18397a4`.
- Stage C is **not flashed**. It will mount p10 rw and start Android.
- Cache remains unset and no cache evidence exists.
- Stage B left `/data/local/xoom-storage-test` with the verified test payload.
- No application compatibility or Android persistence is proven.


## Stage C first boot — 3 November 2026

Stage C booted against repaired p10. The report validates p10 rw, p9/p8/disk RO,
`/data` p10 ext4 rw, `/cache` fresh tmpfs, system ro,noload, Android init
executed, and surfaceflinger/zygote running. A second boot is still required to
prove Android userdata persistence across reboot. No Stage D or cache p9 write.


## Final post-shutdown state — 3 November 2026

After the successful Stage C boot, an Android shutdown hang required a forced
cycle. Journal-only replay cleared p10 `needs_recovery`; final inspection shows
p10 read-only, ext4 magic, incompat `42000000`, ro mount. p9 cache still shows
`needs_recovery` `46000000` and was never mounted or used. Stage C uses tmpfs
cache. No Stage D, cache persistence or content audit.


## Operator persistence confirmation — 3 November 2026

The operator confirmed the persistent Stage C boot retained:

- existing apps;
- accounts;
- `/data/media`, including Photos;
- Wi-Fi configuration.

These are operator observations, not an independent database/content or
credential audit. The operator explicitly declined a fresh post-Stage-C raw
backup. No further write test is required by the operator.


## Reboot-tolerant Stage C — 3 November 2026

New Stage C image `60226983…` accepts only the ext4 needs_recovery bit in
addition to the approved base state, then mounts rw to replay the journal. It
does not run a full fsck or touch cache p9. This is the candidate for repeated
reboot testing; not yet flashed.


## Repeated reboot result — 3 November 2026

Stage C reboot-tolerant image `183597ba…` passed two additional full boots (2a
and 2b) with different pstore boot IDs. Both had p10 ext4 rw, cache tmpfs,
p9/p8/disk RO, and Android SurfaceFlinger/zygote running. No Stage D or cache-p9
write. Third reboot optional.
