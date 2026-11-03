# P9-only offline repair: reviewed procedure, not executable authorization

Prepared 3 November 2026. No physical repair, flash, reboot, writable export,
filesystem mount or tablet command was performed in preparing this plan.
The tablet currently runs the immutable read-only p9 USB backup image. Android
Stage C is not running. Do not confuse host-copy success with physical repair.

## Evidence and scope

Original p9: 536870912 bytes, SHA-256
`7053be21ae7e7c627aa829eafc97501cd5ceae2063f56177a4ce28488b3e4aef`.
Its two complete source reads matched the backup. Source and backup read-only
fsck found journal recovery pending and unset inode bitmap padding.

The operator replayed the journal only on a disposable host copy, corrected only
the reported bitmap padding, then completed all five read-only fsck passes with
exit 0. Repaired copy SHA-256:
`8cf6c18b57eefbf19c31fd5ca81fe44ac016836af9fc97521f1dd80699e5527e`.
The original hash was rechecked unchanged afterward. These results are reported
operator evidence; the preparation utility below independently rechecks them.

Keep original backup, journal-only receipt/intermediate hash, manual repair
transcript and clean-copy evidence. Do not overwrite any of them or upload raw
filesystem contents to GitHub. Duplicate p9/p10 UUIDs are known; use fixed device
identity, geometry, raw hash and independent cache receipts, never UUID discovery.

## Existing components that must not be reused as a writable gate

* `offline98-p10-repair.sh` releases p10 before checking mounts; it also leaves
  the target writable until reboot. It is p10-specific and is not a p9 template
  that can safely be made usable by substituting a pathname.
* `storage-policy.c` always releases p10 first and optionally p9. Cache-only
  repair must never invoke it or carry `/bin/storage-data-approved`.
* The existing read-only p9 backup profile intentionally has no write release.
  Do not weaken it, change host block flags, or run fsck against `/dev/sdb`.
* Existing recovery automatic mounts and tool behaviour are not established for
  this task. Do not boot recovery to do this repair.

A p9-only repair image **does not exist yet**. The following defines its required
contract and operator sequence. No physical commands are approved by this plan.

## Required isolated environment

Use a separate reviewed RAM-only image with no Android, recovery UI, automount,
USB mass-storage LUN, automatic fsck, background writer, automatic reboot or
suspend. Serial diagnostics and checker executable must live entirely in RAM.
Do not use the host repaired image as a block-level restore payload.

The kernel must enforce all ten partitions and the whole disk read-only by
default. A separate repair DT/config and fixed-purpose helper may release ONLY
p9 (major:minor 179:9). Direct whole-disk writes, partition-table writes, all
other partitions and discard/write-zero operations must remain rejected at the
actual request/bio layer, even if a userspace block flag is accidentally cleared.
Prove positive p9 writes and negative p10/p8/whole-disk/cross-boundary writes in
a fixture harness before building. Read-only sysfs flags alone are insufficient.
No restart, voltage, regulator, charging, PM or display changes belong here.

## Preflight before release — all must pass

1. Bind the exact kernel, DT, built-in/runtime archive and e2fsck hashes. Audit
   the archive that actually boots, not just an external unused ramdisk.
2. Validate that exact checker in the same image on RAM fixtures: clean image,
   journal replay, this padding defect, error exit handling, and read-only checks.
   Preserve complete logs and before/after fixture hashes. No marker-only pass.
3. Require Wingray identity and all ten tested BigPart extents, disk 62521344
   sectors. P9 must be start 2215936, length 1048576 sectors, 536870912 bytes,
   ext4 magic and expected feature words; p10 must remain start 3264512, length
   59247616 sectors. Reject alternative aliases, holders or partition devices
   that resolve to anything other than the fixed expected major:minor.
4. Verify all disk/p1–p10 flags RO, no eMMC-backed mounts under ANY pathname,
   no swap, no holders/DM layers, no open competing writer, no gadget export.
   Check both mountinfo device numbers and resolved aliases, not just /cache.
   Quiesce any competing process first; perform these checks BEFORE release.
5. Hash physical p9 while RO and require the original acquisition hash. If it
   differs, stop and acquire new evidence; do not assume the old repair applies.
   Record independent p8/p10 protection/evidence without requiring another full
   29GiB backup. Keep the working Stage C and original boot/recovery images.
6. Confirm host evidence, power, physical recovery buttons and diagnostic path.
   Require a fresh per-boot nonce; preflight/arming must expire after reboot or
   failure. A serial reconnect must not implicitly arm or repeat repair.

## Explicit later execution gate — requires separate authorization

Review the final image and full preflight, then request approval specifically for
physical p9 journal replay and the scoped interactive correction. Merely booting
an offline image is not permission to repair. No current command releases p9.

The proposed transaction must hold verified device descriptors, recheck all
exclusion/protection conditions immediately before release, set only p9 RW,
verify all other protections, and run the fixed checker interactively on p9.
No automatic `-y` or broad repair. Expected operation is journal replay and the
single bitmap-padding correction. Any additional repair prompt is a stop/review
condition. Never format, resize, change UUID/features, restore host bytes, mount
p9, or touch p10/system/boot/recovery/GPT as part of this transaction.

Every normal/error/signal path after release must sync and attempt checked p9
read-only restoration. Require all flags RO, no mounts/exports/holders, then run
read-only e2fsck and metadata/hash collection. No lazy/forced unmount. If relock,
sync, fsck or evidence fails, report failure, retain logs and block Android.
Uncatchable power loss cannot be made transactional: on recovery boot, require
all-RO preflight and new backup/checks before any further operation. Never claim
that ext4 repair rollback can be guaranteed by shell traps.

A corrected-error exit 1 is not a final health pass. Require a subsequent full
read-only fsck exit 0, supported features, no recovery bit/errors, and retained
logs. The physical repaired hash need not equal the host copy (timestamps and
journal metadata can differ); health/identity checks must be independent.

## After successful physical repair — separate later stages

Power-cycle into the immutable p9 backup profile, independently acquire a NEW
post-repair p9 backup with two matching source passes and healthy source/image
checks. Preserve the original dirty backup unchanged. Persistent cache approval
requires that new evidence; host-copy health never substitutes for it.

Only then build and review a separate persistent-cache Android candidate with
fixed p9/p10 identities, p8/disk RO, existing approved p10 evidence, no format or
cache erase, and boot-only restoration instructions. Test clean shutdown first
with tmpfs cache where practicable; it remains unvalidated. Repeated forced
cycles can leave both persistent filesystems requiring journal replay.

Restore Stage C boot only through the already reviewed procedure if abandoning
this experiment; do not flash recovery or repartition. Do not restore an old p10
backup over the user's current data. Restore the host's automount/automount-open
settings (previously true) only after the exported disk has disconnected.

## Host-only evidence preparation command (optional, no tablet access)

```
sudo python3 scripts/prepare-cache-repair99.py \
  --host-inspection /home/justin/xoom-p9-backup99/host-inspection.json \
  --repaired-copy /home/justin/xoom-p9-journal99-2g0q1x3b/cache-working.img \
  --output-dir /home/justin/xoom-p9-repair-preparation99
```

Run from this checkout. This revalidates the original cache evidence and both
hashes, checks the repaired regular HOST file read-only and writes a new private
host receipt. It never opens a tablet device, replays a journal, repairs anything,
changes policy or grants physical approval. Root access is needed only because
existing evidence is root-owned. Keep that receipt local.
