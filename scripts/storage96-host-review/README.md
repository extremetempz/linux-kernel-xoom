# Storage96 host-only review tools

These are the exact project-specific host-copy scripts used in the documented
repair rehearsal, including the corrected noninteractive journal mode,
net_bt_stack3008 mapping and Android platform-package data-directory handling.
They are preserved for review/reproduction, **not a tablet repair launcher**.

They contain fixed local artifact/report paths and acquisition/image hashes for
this operator's experiment. Inspect the source before running. Do not substitute
a block-device path. All writable images are newly created disposable host files;
the original backup is opened only read-only. Debugfs is never passed `-w`.
Scripts require root solely because the private backup/report directories are
root-only. Enter passwords only in the local terminal. They never run ADB,
fastboot, mount, reboot, physical restore, mkfs or write to a tablet device.

Historical sequence:

1. `check-copy.py`: verify acquisition hash while making a new host copy;
   journal-only recovery, then non-modifying fsck. Its first deployed version
   omitted `-p` and refused recovery without a terminal; the committed version
   includes that correction.
2. `resume-journal.py`: fixed-path, single-attempt continuation for that specific
   exit8 refusal. It requires the copy still match the verified acquisition hash.
3. `preen-copy.py`: another independent copy, verified before preen; stop when
   preen needs manual review. The later manual prompt decisions occurred in the
   operator's terminal and are not replayed/automated by this script.
4. `inspect-repaired.py`: recheck hashes/fsck, inspect fixed metadata paths and
   create credential-redacted Wi-Fi/package summaries without mounting.
5. `compare-rom.py`: compare metadata against pinned original boot init rules,
   and inspect reported orphan records read-only. Numeric GID3008 was verified
   from the exact original init binary; the first checker incorrectly used1028.
6. `summarize-rom-comparison.py`: preserve the old report, produce a corrected
   derived report and summarize existing orphan/package evidence. Its input is
   the specific historical report, not an arbitrary new inspection.

The corrected platform-package path handling in inspect/compare has not been
rerun against the operator's images. Existing90 ordinary package UID checks pass;
the platform `android` record must not be treated as a missing ordinary app.
Results, images, directory listings and app names remain private and are not
committed. See `docs/persistent-storage-96-host-repair-review.md` and
`docs/persistent-storage-96-offline-repair-plan.md` for evidence limits and gates.
