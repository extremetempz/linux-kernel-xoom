# Storage96 host-copy repair and compatibility evidence

3 November 2026. This records operator-supplied outputs from the host tools.
No tablet repair, restore, flash, partition change or writable mount was
performed by these experiments. The original verified raw backup is preserved.
Private images, reports, directory listings and credentials are not included.

## Verified acquisition and host experiment

- Raw p10: 30334779392 bytes, UUID
  `57f8f4bc-abf4-655f-bf67-946fc0f9f25b`.
- Original backup SHA256:
  `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579`.
- The acquisition tool reported matching complete independent source reads,
  verified backup bytes and blocked filesystem health.
- Initial read-only fsck skipped journal recovery and reported orphan-list,
  free-count and inode-bitmap padding inconsistencies. The unsupported/recovery
  feature verdict was specifically needs_recovery (incompat 70 = 2+4+64).
- Journal-only recovery on a separate host copy returned0 and cleared recovery;
  full read-only fsck still returned4. Journal replay alone was insufficient.
- Conservative preen on another copy stopped with4 at the orphan list.
- The operator manually accepted the individual orphan-list, free-block,
  free-inode and bitmap-padding corrections on that disposable image only.
- Subsequent full read-only fsck completed all five passes with exit0.
- Repaired experimental image SHA256:
  `9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f`.
- The later read-only inspection reverified the original backup hash, recorded
  the repaired hash, repeated passing fsck and confirmed repaired bytes unchanged.

## What the repair evidence establishes

All20 inode numbers printed in the orphan-list repair were already marked not
in use, with link count0 and size0, in both original and repaired images.
This supports stale orphan metadata for those records; it does not identify
their historical contents or prove the integrity of every application file.

The original check already counted6805492 free blocks and1827448 free inodes.
Those are the corrected counters. Therefore the change from16800 to16712
reported allocated inodes and600204 to600076 reported blocks does **not** by
itself prove that repair removed88 live inodes or128 allocated blocks. Earlier
wording describing them as newly released allocations was too strong. A complete
allocation/reachable-file comparison was not performed. Do not claim lossless
recovery or diagnose when the original inconsistencies arose.

## Compatibility evidence

The pinned original boot SHA256 is
`64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
Its saved system build properties identify EOS Android4.4.4, API19, matching
userdata's internal/external platform versions19.

-91 package records were checked;90 ordinary package directories existed and
  none had a UID mismatch. The other record is the platform `android` package,
  UID1000, code path `/system/framework/framework-res.apk`. It must be treated
  specially, rather than demanding `/data/data/android` like an ordinary app.
  The checkers now inspect the corresponding `/data/system` metadata for this
  exact platform record. That corrected individual result has not been rerun.
- No genuine mismatch was found in the inspected init-controlled metadata.
  The sole reported mismatch, bluedroid GID3008, was a checker bug: it incorrectly
  mapped net_bt_stack to1028. Direct examination of the pinned ARM init's numeric
  name/ID tables confirms3008;1028 is sdcard_r. The checker was corrected, and
  its derived corrected report has an empty mismatch list. No chown is required.
- The saved Wi-Fi configuration is regular/readable and contains one network,
  with the expected socket directory used by original and generated init.
  SSID/password values were neither saved in reports nor printed. This is
  configuration evidence, not a connectivity test of repaired userdata.
- Only one of25 inspected existing paths had a SELinux label. The reviewed
  Linux4.4 config has SECURITY and EXT4_FS_SECURITY disabled and its generated
  command line requests disabled SELinux. Missing labels therefore do not alone
  establish a boot blocker for that profile. Original2.6 kernel has SELinux
  support compiled; saved evidence does not establish its runtime enforcing
  mode. Returning this data to that environment requires separate label review.

## Remaining gate

The host experiment is structurally clean and no inspected ordinary ownership
or Wi-Fi-layout incompatibility was identified. Application database/content
integrity and an Android boot using repaired data remain unproven. The tablet's
original userdata was not repaired and remains blocked by its original evidence.
Do not substitute the repaired host copy's verdict into readiness for the
unmodified tablet. Do not restore or repair physical userdata without a concrete
offline recovery plan and explicit operator authorization. Retain the verified
raw backup, journal-only intermediate, repair experiment and all private logs.
After an authorized physical repair, acquire fresh read-only filesystem evidence
before the separately approved controlled two-boot write test. Keep unverified
cache temporary and LP2 out of the initial persistence experiment.
