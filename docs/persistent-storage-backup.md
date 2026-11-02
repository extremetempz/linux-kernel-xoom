# Userdata backup gate for persistent storage

**No verified off-device p10 backup exists in this workspace.** Stage B and
Stage C are therefore not authorized.

## Required object

A restorable raw image of the existing userdata partition:

```text
source: /dev/block/mmcblk0p10
size:   59,247,616 sectors = 30,334,779,392 bytes
```

The backup must be taken with p10 **not mounted read-write** and must be
verified by size and SHA-256. A boot-image backup is insufficient.

## Acquisition options

Use an environment and procedure you already trust; this repository does not
flash recovery, repartition or automate userdata writes.

- Existing recovery/TWRP that can read the BigPart p10 without restoring or
  formatting it, with output to an external SD card or ADB stream.
- Existing original Android with a verified root shell, p10 unmounted, and
  output to a removable medium.
- Any offline method that yields the exact partition byte stream.

Example command shape only, to be run by the operator in such an environment:

```sh
# Confirm p10 is not mounted and the external target is not p10/cache/system.
dd if=/dev/block/mmcblk0p10 of=/path/to/external/p10.img bs=4M conv=fsync,noerror
sha256sum /path/to/external/p10.img
stat -c %s /path/to/external/p10.img
```

Do not run a command like this against a path you have not verified. Do not
write the backup into p10 itself. Do not commit it to GitHub.

## Verification

```sh
python3 scripts/persistent-readiness.py \
  --inspection artifacts/storage-inspect1/inspection.json \
  --backup /path/to/external/p10.img \
  --backup-sha256 <sha256> \
  --output artifacts/storage-inspect1/write-readiness.json
```

This only verifies the Stage-A verdict, exact p10 size and SHA-256. It does not
flash, mount or authorize a physical write.

## Restore

Restoring boot does not undo changes to `/data`. A userdata restore is a raw
write to p10 using the verified backup and an operator-approved offline
procedure. Do not format, repartition or factory-reset. Preserve the current
backup hash and stop if the target size does not match.
