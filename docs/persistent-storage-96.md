# Persistent storage review and read-only candidate96 — 3 November 2026

Base main: `525dc6d499`. This continues the existing94 implementation.
No ADB/fastboot/device command, flash, reboot, mount or tablet write was performed.
The other working checkout and all existing private images/captures were preserved.

## Current status

| Component | Implemented / offline tested | Physical evidence | Blocker / next action |
|---|---|---|---|
| Android/GPU/touch/radios/battery | Existing stack retained; selected regression tests pass | Earlier Android and radio results remain authoritative | No new combined hardware test here |
| LP2 | Existing code unchanged; LP2 offline tests pass | One genuine cycle and94 CPCAP-order pass; repeated `-EBUSY` remains | Do not combine initial storage work with LP2 tests; no automatic LP2 |
| BigPart | Existing mapping retained;1000-capacity geometry tests pass | Full capacity/ten partitions already reported | Never rewrite GPT or substitute legacy recovery geometry |
| Android filesystem inspection | Existing inspector/parser retained | Private inspect2/3/post-B reports show RO mounts; fsck139/127 | Android tool crash is not filesystem-corruption proof |
| Read-only USB backup |96 validates geometry before binding, immutable backing policy, one RO p10 LUN, no Android/serial |94 backup artifact exists; no accepted host inspection/backup bundle found | Next physical stage is host read-only inspection/acquisition |
| Policy helper | BLKROGET pointer fixed, checked flag/status/capacity, transactional cleanup; ARM build and fault tests pass | Local B debug says P9_ROGET_NOT_ZERO; no successful B marker | New helper is not hardware-validated; old94 writer is not approved |
| Kernel write isolation | Original partition policy checked before bio remap; ioctl/open protection retained; compiled path tests pass | No protected-partition write test attempted | Validate only safe data stage after backup; never probe boot/system with writes |
| Backup readiness | Host captures, independent direct source reread, image hash, raw metadata and tool logs required | No verified off-device p10 evidence bundle supplied/found in reviewed artifact paths | StageB/C blocked |
| Controlled file test | Exclusive payload/stamp, UUID, different boot ID, no overwrite/retry; fixture tests pass | None accepted | Requires clean host inspection, backup, code review and physical-write approval |
| Persistent Android | Existing mounting/integration retained with stronger gates; unverified cache stays tmpfs | No accepted persistent Android/reboot evidence | StageC remains blocked pending two-boot test and compatibility review |

Latest documented working LP2 baseline is `lp2g-ready`, SHA256
`cefb6d82198bb9b516bd01be6b3a815331c541c6c419cf6fb4f7a1a842d52b6e`;
the local file matches.95 is a diagnostic for the later `-EBUSY`, not a proven
replacement. No claim of production-ready sleep or measured savings is made.

## Actual local94 artifacts and newer evidence

The four named files exist in the other local checkout. Actual hashes:

| Artifact | Actual SHA256 | Matches documented94 hash? |
|---|---|---|
| persistent94-inspect | `653cfcdeb7d5ee7ae0ffd74f70f898b9cd774d04bbf222f939617fa53882f496` | No |
| persistent94-write-test | `1a6b041b0b5797d57c18844d66fd4408eda0e6a55bde3178defe69441a633d51` | No |
| persistent94 Android | `3c01d128adf4fe9ee4547a0f56707060c066e0f162377fcf853a71dceace93c1` | No |
| storage-backup94 | `7641d644655e88c012701ca0adafb58e6b4e0565f0615e74344381da179c0979` | Yes |

Sizes match the recorded4222976/4225024/4225024/4231168 bytes. Hash divergence
is not diagnosed as corruption: local rebuilding is one possibility, not a
verified explanation. None was overwritten. Do not identify an image by its
folder name alone.

Newer private local captures exist: storage-stageB1/B2/debug and
storage-post-stageB-inspect. They stop at `FAILED_storage_policy`; debug adds
`P9_ROGET_NOT_ZERO`. No successful fixed-file write/persistence marker was
found. B captures have failed capture status; they are not accepted StageB
proof. Post-B still has a blocked inspector verdict. Uncommitted local helper
changes already corrected the pointer and added error labels, but lacked
transaction rollback. They were reviewed, not overwritten or committed as if
all were validated. There is no basis to claim current filesystem health or
absence of every possible historical write from those logs.

## Defects and corrections

### Userspace ioctl ABI

Linux4.4 `block/ioctl.c` routes BLKROGET to
`put_int(arg, bdev_read_only(bdev) != 0)`. The return is status, not the flag.
The old NULL argument can return EFAULT. BLKROSET also reads an `int *`.

`diagnostic/storage-policy.c` now:

- checks the actual NUL-delimited Wingray compatible and persistent marker;
- refuses firstboot/inspection/backup profiles and missing built-in approval;
- opens fixed direct p10/p9 nodes with NOFOLLOW, checks expected capacities;
- keeps descriptors through the transaction, starts from known RO state;
- defaults to p10 only; p9 requires its own separately built approval;
- passes valid `int *` values, checks status and actual readback;
- restores both selected policies to RO on a partial change, checks cleanup,
  closes descriptors, handles ambiguous close errors with a bounded RO cleanup;
- refuses repeated invocation against an existing RW owner without changing it.

Cleanup failures are reported as failures, never as clean rollback. No software
can guarantee cleanup if the kernel/backend refuses even the RO request. The
bootstrap stops before mounting in that case; preserve evidence and recover,
never retry RW automatically. The initial RO state is established at boot.
The new helper does not explain the later local NOT_ZERO observation by itself:
that needs a matched candidate/report. We have not attributed it to the NULL bug.

### Selective block writes

In this donor `set_disk_ro()` sets part0 and existing partition policies;
`set_device_ro()` changes only the selected `bd_part->policy`;
`bdev_read_only()` reads that partition policy. Therefore a RO whole-disk
alias can coexist with released p10. MMC's main `md->read_only=0` permits
opening that selected partition; hardware boot areas stay protected. Driver
BLKROSET filtering and generic capability checks remain. The VFS write-open
and write-iterator paths check partition RO. Raw MMC commands are rejected,
and RO whole-disk BLKPG/reread guards prevent partition-alias edits.

Open checks alone are insufficient for already-open descriptors or kernel
bios. Patch0178 marks only Wingray policy disks and rejects write/discard/
write-same bios against a RO original bdev **before** `blk_partition_remap`.
Thus a protected alias remains rejected, while legitimate p10 bios are not
mistaken for writes through part0 after remapping. Bounds checks remain.
This is source/compiled-fixture validation, not a hardware isolation claim or
a security sandbox against arbitrary privileged kernel code.

### Backup and bootstrap

The old backup branch bound USB before the shared geometry checks.96 checks
all ten exact extents/capacity/RO flags first. Its overlay restores the
immutable `xoom-firstboot-ro` policy and removes the persistent-release marker.
Only `/dev/mmcblk0p10` is bound with `ro=1 removable=0 luns=1`; module failure
stops. The generated backup fstab has no Android filesystem mounts. Android
never starts, and serial/ACM are absent by configuration.

In the existing gadget source, a RO LUN opens its backing file O_RDONLY;
SCSI writes return SS_WRITE_PROTECTED before file I/O. Kernel backing
protection independently rejects policy release/raw commands and bios. Host
capacity/RO/identity and actual enumeration still require physical checking.
No destructive SCSI write experiment is necessary or requested.

Writable bootstrap now requires an embedded approval created only after host
evidence revalidation. No approval is present in96. StageC approval is not
generated until its separate two-boot/compatibility gate is implemented and
reviewed. Unknown inspection or a JSON readiness boolean cannot start RW mounts.

Approval also binds UUID/features and requires a clean/error-free superblock before
policy release. StageB cleanly unmounts data before awaiting manual reboot. Do not
boot another ROM between host evidence acquisition and an approved test; any
intervening changes require fresh evidence/backup.

Data/cache readiness are independent: default policy releases p10 only, and
/cache remains the already-used96MiB tmpfs. No p9 RW fstab entry is generated.
The host backup image does not inspect p9; no cache approval is issued here.
`nomblk_io_submit` is Opt_removed in this4.4 ext4 parser and was removed from
future RW options. `errors=remount-ro` replaces panic; default journal/barrier
and flush behaviour are retained, without noload on a later approved RW mount.
System remains ro,noload. No modifying fsck, format or cache wipe is added.

### Existing Android data and controlled test

The same pinned original system/init/services/UIDs and policy files are reused;
no new user database or migration is introduced. Wi-Fi configuration is only
created when absent, now also refusing a dangling symlink. Existing credentials
are not replaced. Existing init directory/restorecon actions still need review
against actual userdata metadata before StageC; do not call compatibility proven
because system files match. The host procedure below checks directory metadata
without displaying credentials. Encryption, unknown features or a dirty journal
block writable use. StageB records filesystem UUID and first boot ID; same-boot
reruns cannot falsely report persistence. A partial stamp/file blocks retries.
Existing unsafe ownership, permissions, symlinks or hardlinks are refused.
No existing application, settings, Dalvik, media or Wi-Fi file is wiped.

## Reproducible source and offline checks

The exported series had overlapping/already-applied LP2 hunks in0171/73/74/75.
Those exports were corrected without changing the effective LP2 implementation.
0177 exports the previously local-only backup DT/config.0179 exports existing
configuration integration differences needed to reproduce the current local
source. This is not a new radio/LP2 implementation. The reconstructed series
matches all218 changed kernel files against the working source tree.

Full ARM kernel/modules build, static non-NEON policy helper, final linked RAM
archive, boot audit and deterministic repack pass. Fifteen selected test
programs pass, including seven host-evidence cases, compiled actual ioctl/helper/
bio paths, partial failures, readonly gates, StageB fixture cycles, Android
bootstrap/archive, Wi-Fi, Bluetooth and LP2 source tests. BigPart's1000-capacity
checks pass separately. See [sanitized results](storage96-offline-checks.json).
These do not establish a physical backup, write persistence or a new LP2 result.

## Candidate96

Local path: `artifacts/storage96-reviewed-ready/wingray-android44-storage-backup.img`

- Size4231168 bytes.
- SHA256 `72717d7d7de316bba4bbbdc910b5668397d7a9b6e4b6aff275c43f2b1549fbac`.
- Kernel source `66ad4c39`; profile `storagebackup`.
- Kernel config, DTB, System.map, generated init/fstab, runtime, boot audit,
  manifest, SHA256SUMS and offline results are alongside the image.
- Static helper/manifest: `artifacts/storage96-policy` (not executed physically).
- Private ROM-containing images and logs are not uploaded to GitHub.

Build with new directories, after applying the series and preserving inputs:

```sh
XOOM_ANDROID_GPU_PROFILE=storagebackup \
XOOM_BUILD_ROOT=/tmp/xoom-storage96-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/storage96-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/storage96-new-ready" \
JOBS=6 bash scripts/build-android-gpu.sh
```

## Next physical stage only: read-only p10 inspection and backup

**No flash is authorized by these commands.** Review96 first; its later boot-only
deployment requires an explicit instruction. Do not deploy old94 writable images.
After the reviewed backup environment has been booted under operator control:

1. Before attaching its new USB mass-storage gadget to the Linux VM, disable
   desktop automount. Record the prior service state. A runtime mask prevents
   D-Bus from restarting UDisks during acquisition:

```sh
systemctl is-active udisks2.service
systemctl is-enabled udisks2.service
sudo systemctl mask --runtime --now udisks2.service
```

Close disk managers/file-browser windows; do not click the new volume. Attach
only the new Linux File-Stor Gadget to VMware. The Motorola logo is expected:
this environment starts neither Android nor the serial diagnostic gadget.
If the host used another automounter, disable it too before attachment.

2. Identify, never guess, the exported disk:

```sh
lsusb -d 0525:a4a5
lsblk -b -o NAME,PATH,SIZE,RO,TYPE,MODEL,TRAN,MOUNTPOINTS
findmnt
```

Require a newly attached USB LUN, expected gadget identity, **30334779392 bytes**,
RO1, no mounted source/child and no unexpected second LUN. Do not use the host's
system disk, the whole Xoom eMMC, or a disk identified only by size. Replace
`/dev/sdX` below only after these checks:

```sh
sudo blockdev --getsize64 /dev/sdX
sudo blockdev --getro /dev/sdX
```

Stop for any mismatch. Do not change the RO flag. No write probe is requested.

3. Choose a new directory on an independent **local host block filesystem**,
with at least32GB free, outside the repository. The tool rejects mounted source,
wrong USB identity/size, non-RO source, source-backed/stacked output and unknown
output backing. Network/shared-folder output is intentionally not accepted by
this first validator. Run from the repository:

```sh
sudo python3 scripts/host-storage-backup.py \
  --device /dev/sdX \
  --output-dir /path/on/host-disk/xoom-p10-backup96
```

This command reads the tablet only. It captures complete `dumpe2fs -h` and
`e2fsck -f -n` stdout/stderr and exit statuses; reads raw superblock/feature/
journal-recovery/error/encryption metadata; copies exactly30334779392 bytes;
fsyncs the host file/directory; and performs a second full source read with
O_DIRECT (no silent buffered fallback). It compares source digests and rehashes
the saved image, then checks the image with host tools. Before/after host kernel
logs must retain a common prefix and no new matching USB/block I/O error. Log
rotation, unsupported features, uncertain health or read/hash errors block
readiness. This conservative filter can require manual review for unrelated
host USB errors; do not delete the evidence to make it pass.

Do not run this against a changing original-Android filesystem. No conv=noerror,
repair, truncation, formatting or automatic retry occurs. A failed/partial image
and complete diagnostic output are retained. Even a dirty/encrypted filesystem
may be copied read-only for preservation. A verified raw copy can be reported
separately while filesystem readiness remains false; it is never approved for RW use.
Two30GB source passes and a backup rehash may take substantial time.

4. Review **all** filesystem output, not only exit0. Codes1/2/4/8/16/32/128 and
signals are blocked, not auto-repaired. State must be clean, no needs_recovery,
no recorded filesystem errors, supported feature subset and no encryption
candidate. `host-inspection.json` alone is insufficient: retain the entire
private bundle, receipts, logs and raw image. Revalidate offline:

```sh
python3 scripts/persistent-readiness.py \
  --host-inspection /path/on/host-disk/xoom-p10-backup96/host-inspection.json \
  --output artifacts/storage96-host-readiness.json
```

The script rereads underlying evidence, verifies targets/log hashes, checks the
backup size/metadata/hash and independent source receipt, and runs actual offline
policy tests. It emits separate DATA_FILESYSTEM_VERIFIED, DATA_BACKUP_VERIFIED,
DATA_WRITE_POLICY_VERIFIED, CACHE_FILESYSTEM_VERIFIED, CONTROLLED_WRITE_TEST_READY
and ANDROID_PERSISTENT_BOOT_READY fields. `writes_allowed` remains false: readiness
is not physical-write permission. Cache and Android readiness remain false here.
Original Android StageA results may be referenced with --inspection; they are
not overwritten or treated as healthy host evidence.

5. Only after clean inspection and complete backup, optional host read-only
layout review may use `mount -t ext4 -o ro,noload,nosuid,nodev,noexec` on the same
RO LUN, then `stat` directory ownership/modes and SELinux xattrs for app/data/
media/misc/wifi. Do not display or edit credential contents. Unmount afterward.
Any UID/layout/label mismatch is a blocker to StageC, not permission to wipe.
Do not run LP2, StageB, package installation or Android RW tests in this stage.
After disconnecting the gadget, remove only the runtime mask you added; restart
UDisks only if it was active before. Never unmask a pre-existing permanent mask.

## Recovery / restore capability

A working original boot backup SHA is
`64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`;
recovery backup SHA is
`5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.
They are preserved. Only after explicit instruction, manual fastboot can restore
**boot**; do not flash recovery or alter the partition table. Verify full
boot/recovery readback when returning to the original ROM.

Boot restoration cannot undo future userdata writes. A raw restore requires
separate explicit approval and a trusted **BigPart-aware offline writable**
environment, not this immutable backup image. Verify the raw image hash against
both acquisition and independent-source receipts, then verify destination device
identity, all BigPart extents and p10's exact59247616 sectors/30334779392 bytes.
Require p10 and aliases unmounted, no encryption mapper or Android writer, and
check the fixed destination `/dev/block/mmcblk0p10` is the actual BigPart userdata.
Only then may an operator copy the verified image with checked `dd` plus fsync,
without noerror/notrunc shortcuts or formatting. Re-read the complete destination
and compare SHA256 afterward; any short read, write or I/O error stops recovery.
Do not use `fastboot flash userdata` with an unverified legacy partition view.
No restore was executed and no verified userdata backup currently exists here.
