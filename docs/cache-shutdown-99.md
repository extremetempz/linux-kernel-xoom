# Persistent cache and clean shutdown preparation — 3 November 2026

Reviewed main through `982b736` (PR40). This work is isolated on
`codex/shutdown-cache`. No device operations, filesystem repair, flash or reboot
were performed. Existing Stage C image and all backups remain unchanged.

## Verified baseline and findings

Stage C image SHA-256:
`183597ba60580729bfaadfaf642b073a477bb494e3d1b09cd6da2ac629d398da`.
Persistent p10 boots; cache is tmpfs; p8/p9/disk stay read-only. Existing reports
record three boot IDs and the user confirmed apps/accounts/media/Wi-Fi.

The shutdown request was intentionally rewritten by `transform_init()` to only
record `sys.powerctl`. It never invokes native `powerctl`. This is a confirmed
software blocker, not a complete diagnosis of every possible shutdown failure.
The tested persistent kernel also lacks CONFIG_POWER_RESET. Simply restoring
native powerctl therefore does not establish electrical poweroff.

Original Motorola `board-stingray.c` poweroff drives PV7/WDI low. The isolated
profile reuses the donor Wingray power driver with a new poweroff-only mode:
PV7 is claimed inactive/high and asserted low only in its poweroff callback.
That mode does not access CPCAP VAL1 or register restart/notifier paths. GPIO
ownership, shutdown sequencing and actual electrical poweroff remain untested
on this new profile. No charging limits, regulators, CPU voltages or PM states
are changed.

## Changes

* Patch 0180 exports the existing cache-specific, immutable read-only USB backup
  profile. It exposes only p9; Android does not start. All partition geometry and
  read-only checks run first. It performs no journal replay or repair.
* Host backup acquisition accepts explicit `--partition cache`, binds exactly
  536870912 bytes, `cache-p9.img`, independent second-read hashes and a separate
  p9 evidence schema. Data evidence cannot substitute for cache evidence.
* Persistent-cache preparation requires healthy independent p9 evidence and
  existing p10 approval. UUID/features are rechecked on the device before policy
  release. Default Stage C remains tmpfs cache. A dirty p9 currently cannot pass.
* Full filesystem feature words are now checked even when only ext4 journal
  recovery is allowed after a forced power cycle; other feature changes fail.
* Patch 0181 adds an opt-in `persistentshutdown` profile. Existing profiles retain
  their diagnostic log-only powerctl behaviour. Init stops Android service
  classes before the helper performs bounded sync, ordinary unmount or checked
  read-only remount, rejects writable eMMC aliases, and requires clean p10 (and
  independently approved p9, if present) before native shutdown/reboot handoff.
  Unsupported reboot targets are not forwarded. Failure stops the handoff and
  leaves RAM diagnostics; it does not guarantee Android services recover.

## Offline validation and outputs

Read-only cache profile: complete ARM kernel/modules/runtime build and packing
passed. Image:
`artifacts/cache-ro-reviewed-ready/wingray-android44-cache-backup.img`
Size: 4235264 bytes. SHA-256:
`8bd8b70aebf693fec173ff9adda12aa3a2f60e85889b6094fa0da95eac80521d`.
The reviewed repack produces identical image bytes. Manifest describes p9.
Artifacts are local/ignored; source commits do not upload private ROM inputs.

Shutdown profile: ARM zImage-dtb and modules compile successfully, including the
poweroff-only driver. The compile used an empty runtime archive solely to check
kernel linking. **That kernel is not a ready-to-flash Android image.** Full image
preparation still requires the existing protected post-repair p10 evidence and
Stage B proof. Their checks were not bypassed. Use the standard builder with:

```
XOOM_ANDROID_GPU_PROFILE=persistentshutdown
XOOM_STORAGE_HOST_EVIDENCE=<validated post-repair host-inspection.json>
XOOM_STAGEB_PROOF=<validated stageb-two-boot-proof.json>
```

Set these as environment variables when invoking `scripts/build-android-gpu.sh`.
Do not set `XOOM_CACHE_HOST_EVIDENCE` until separate healthy p9 evidence exists.
Apply patches 0180 then 0181 to the reviewed donor before selecting the profiles.
Keep build/runtime/image output paths separate from the known-good artifacts.

Tests cover actual helper shell execution using fixture commands, successful
unmount and read-only fallback, sync/busy/alias/dirty failures, dirty approved
cache blocking, source identity and recovery-bit masking, host evidence binding,
Stage C versus explicit persistent-cache report policy, default image generation
and existing serial framing. These tests prove software checks, not hardware
shutdown, storage durability or physical poweroff.

## Next hardware stages (not performed or authorized here)

1. Review and separately approve booting the immutable p9 USB backup image.
2. Identify its host block device using exact size/read-only identity, then use
   `host-storage-backup.py --partition cache` with a new output directory. Never
   guess `/dev/sdX`. Preserve its original backup unchanged.
3. If `needs_recovery` remains, inspect journal replay/repair on a disposable host
   copy first. No physical p9 repair tool or blanket write authorization is added.
4. Build the shutdown profile with valid p10 evidence and tmpfs cache first.
   Approve a separate boot-only test, collect shutdown stages, confirm physical
   poweroff, then cold-boot and verify p10 cleanliness and existing Android data.
5. Only after p9 repair and independent evidence review, test persistent cache.
   Confirm p8/disk remain RO, p9/p10 identities and mounts, repeated clean shutdown
   and cold boots, app/media/Wi-Fi/Bluetooth continuity and filesystem health.

Rollback uses the preserved Stage C boot image through the existing verified
boot-only restoration procedure. No recovery/partition-table overwrite, format,
factory reset or implicit p9 repair is part of this change. Keep the host backups
and original boot/recovery images. New poweroff and persistent-cache hardware
behaviour remain unvalidated; neither is reported as working.

## First p9 acquisition — physical read-only test

The p9 image was boot-flashed with user authorization. Host enumeration initially
failed configuration with -32; a USB reconnect succeeded before acquisition.
The host then reported exactly 536870912 bytes, write-protected, unmounted.
The operator ran the independent two-pass acquisition and reported
`CACHE_BACKUP_VERIFIED; CACHE_FILESYSTEM_BLOCKED`.
Backup SHA-256: `7053be21ae7e7c627aa829eafc97501cd5ceae2063f56177a4ce28488b3e4aef`.
Both source and backup read-only fsck report skipped journal replay and invalid
inode bitmap padding. Metadata: incompat=70 (includes recovery), state=1,
error_count=0. These are not healthy-filesystem evidence.

P9 UUID equals the previously recorded p10 UUID. Duplicate UUID alone is not a
partition identity failure: the implementation uses fixed p9, exact capacity,
independently bound cache evidence, geometry and current superblock checks.
The builder's unnecessary distinct-UUID requirement is removed; zero UUID is
still rejected. No mount-by-UUID selection is introduced.

`scripts/check-cache-copy99.py` verifies the original hash, makes a new 512MiB
host copy, verifies it, replays only that copy's journal, then runs read-only
fsck. It stops on remaining errors and does not perform general repair, open a
tablet device, alter the original backup or authorize physical writes. Its
results are pending. Persistent cache remains blocked. Desktop automount was
temporarily disabled (both previous settings true); restore only after the
exported disk is disconnected. The tablet currently runs the read-only p9
backup image, not Stage C; restoration is still pending.

## Clean host copy and offline procedure preparation

The operator corrected only inode bitmap padding on the journal-replayed HOST
copy. A subsequent five-pass read-only e2fsck completed exit 0. Original backup
hash remained unchanged; clean copy hash is
`8cf6c18b57eefbf19c31fd5ca81fe44ac016836af9fc97521f1dd80699e5527e`.
See [p9-only offline repair procedure](cache99-offline-repair-plan.md) for the
reviewed protection contract, unresolved kernel/runtime requirements and optional
host-only receipt tool. No p9 repair image or physical write approval is supplied.
