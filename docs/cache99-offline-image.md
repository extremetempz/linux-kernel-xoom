# Cache99 isolated p9 repair candidate — built, hardware pending

User requested build and boot-only flash followed by operator instructions.
Original and repaired-host evidence was independently rechecked by the operator:
`host_copy_check_passed=true`, preserved hashes unchanged, full fsck exit 0.
This supersedes the earlier plan's statement that no candidate image exists.

Image: `artifacts/cache99-offline-ready/wingray-cache99-offline-repair.img`
Size 3897344 bytes; SHA-256
`3474beffbe46e3ee8c2547b2d157239ab63ec61a81c614dd3137b43b7bbe74d2`.
It is locally built and offline-checked, **not hardware validated** at preparation.
The former read-only backup image and Stage C image are unchanged.

## Kernel and transaction protections

Patch 0182 adds a separate profile with all media initially RO. A repair-specific
kernel disk flag rejects writes to any partition other than p9 even if a RO flag
is cleared. Discard and write-same are forbidden, including on p9. Raw MMC and
partition-table ioctls remain forbidden. Existing persistent/backup profiles keep
their previous behaviour; no old helper has been repurposed to release p10.
The separate helper can open only `/dev/mmcblk0p9`, checks exact capacity and
profile markers, rejects a data approval token, and has a separately compiled RO
lock variant. No mass-storage export, Android or automatic repair exists here.

PID1 reconstructs and hashes the known checker into RAM, then runs clean and
counter fixtures plus a new synthetic journal/padding fixture. No private cache
contents are embedded. Preflight requires RAM pass, exact disk/all-ten geometry,
all-RO flags, fixed device numbers, virtual-only mounts, no eMMC mount aliases,
no holders, no swap, no mass-storage gadget and the original physical p9 hash.
The server requires preflight with the same nonce before arming. Confirmation
expires after 60 seconds; a new serial session invalidates the pending nonce.
The repair wrapper repeats preflight before release, allows a single attempt,
runs interactive e2fsck, syncs, relocks p9 and verifies all disk/partition flags.
An uncertain release, repair failure, sync failure, relock failure or unsuccessful
read-only fsck prevents a success report. Signals attempt cleanup; power loss
cannot guarantee rollback. Do not boot Android following any failed transaction.

## Offline validation

Full ARM kernel links with the actual built-in runtime. Packing verifies the
compiled compressed initramfs byte-for-byte against the prepared archive,
helper/source hashes, empty external ramdisk, appended DTB and ARM zImage layout.
Compiled DT is compared against persistent: only model and two repair markers
change. Existing Motorola wiring/voltages/display/PM settings are retained.

`test-storage-policy96.py` compiles actual ioctl/bio paths: p9-only release,
immutable p10/other partitions/whole disk even with cleared RO flags, and denied
discard/write-same. `test-cache99-policy.py` tests actual fixed helper logic and
ioctl failure rollback. `test-cache99-repair.py` executes the real shell with fake
commands: preflight-first, uncertain release, repair/sync/relock/recheck failures.
`test-cache99-report.py` rejects incomplete or contradictory RAM/geometry/mount/
write-policy reports. Existing protocol suite passes. Synthetic host fixture
returns checks 4, journal replay 0, padding check 4, preen 1, final check 0.
The ARM checker still must demonstrate these results on this image on hardware.

## Build/reproduction

Apply exported patches through 0182 to the reviewed donor. Select
`wingray_cache_repair99_defconfig`; retain the standard toolchain/build flags.
Create the synthetic fixture with `scripts/build-cache99-fixture.py`, then use
`scripts/prepare-cache99-runtime.py --help`. It takes the prior validation
archive (checker chunks and original fixtures), pinned BusyBox, fixture archive
and standard build-root layout. Copy the generated runtime.cpio to the configured
`out/usr/wingray-android-runtime.cpio` before building zImage-dtb. Pack only after
building using `scripts/pack-cache99-image.py`. Do not use an old kernel with a
new external ramdisk; the runtime is built into the kernel.

## Staged operator instructions

1. Boot-only deployment of this candidate is authorized by the latest user
   request. Do not flash recovery or any data partition. Motorola logo is normal.
2. Connect its Linux USB Serial Gadget to VMware. Grant temporary tty access if
   needed. Capture a fresh `offline-cache99` report and require actual RAM tests,
   all-ten geometry, all-RO live flags and no attempted repair. Do not use the
   older marker-only offline97 parser as this gate.
3. Only after reviewing that report, open the serial terminal, with complete host
   transcript recording. Run `PREFLIGHT_P9 <32-lowercase-hex-nonce>` and require
   `CACHE99_PREFLIGHT_PASSED_P9_RO_ALL_OTHERS_RO`.
4. A separately deliberate `REPAIR_P9 <same-nonce>` arms, and
   `REPAIR_P9_CONFIRM <same-nonce>` within 60 seconds starts the physical action.
   Do not send either command before reviewing the RAM and physical preflight.
5. Expected interactive correction is journal replay plus only the inode bitmap
   padding fix. Answer yes only to that reviewed padding prompt. If a different
   repair is requested, stop (Ctrl-C) and retain the complete output.
6. Require repair exit 0/1, checked all-RO relock, five-pass read-only recheck exit
   0 and `CACHE99_REPAIR_COMPLETE_REQUIRES_NEW_READONLY_BACKUP`. Any other result
   blocks subsequent Android/cache activation.
7. Return to fastboot; boot the immutable p9 backup image again; independently
   acquire a NEW post-repair p9 evidence bundle. Keep dirty original unchanged.
   Never require equality with the repaired-host hash: timestamps may differ.
8. Persistent-cache Android build and boot remain separate later actions, gated
   by the new healthy physical evidence. If stopping, restore the exact Stage C
   boot image, never an old p10 backup. No physical p10 restore is part of this.

Current baseline Stage C hash:
`183597ba60580729bfaadfaf642b073a477bb494e3d1b09cd6da2ac629d398da`.
Current p9 backup image hash:
`8bd8b70aebf693fec173ff9adda12aa3a2f60e85889b6094fa0da95eac80521d`.
Host automount settings were originally true and remain temporarily disabled;
restore them only after the exported storage gadget is disconnected.
