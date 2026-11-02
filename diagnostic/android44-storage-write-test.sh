#!/bin/busybox sh
# Manual Stage B only, after host inspection/backup and an approved boot image.
BB=/bin/busybox
OUT=/run/android44-storage-write-test.txt
DIR=/data/local/xoom-storage-test
FILE=$DIR/persistent-v1.bin
STAMP=$DIR/first-boot-v1
EXPECT=4f5a76d96d52a7902acb25f86971d101fc9fae1d7d97039fb6f0fbbb0a7e13ee
umask 077
: > "$OUT"
say() { echo "$@"; echo "$@" >> "$OUT"; }
stop() { say "$1"; say XOOM_STORAGE_WRITE_TEST_END; exit 1; }
regular() { [ ! -L "$1" ] && [ -f "$1" ] && [ "$("$BB" stat -c '%u:%g:%a:%h' "$1")" = '0:0:600:1' ]; }
say XOOM_STORAGE_WRITE_TEST_BEGIN
[ "$#" = 0 ] && [ "$("$BB" id -u)" = 0 ] || stop INVALID_CALLER
[ -f /bin/storage-data-approved ] || stop READINESS_MISSING
[ "$("$BB" awk '$2=="/data"{print $1" "$3}' /proc/mounts)" = '/dev/mmcblk0p10 ext4' ] || stop DATA_MOUNT_UNEXPECTED
[ "$("$BB" cat /sys/block/mmcblk0/mmcblk0p10/ro)" = 0 ] || stop DATA_READONLY
boot=$("$BB" cat /proc/sys/kernel/random/boot_id) || stop BOOT_ID_READ_FAILED
uuid=$("$BB" dd if=/dev/mmcblk0p10 bs=1 skip=1128 count=16 2>/dev/null | "$BB" od -An -v -tx1 | "$BB" tr -d ' \n')
say "BOOT_ID $boot"
say "DATA_FILESYSTEM_UUID $uuid"
[ "${#boot}" = 36 ] && [ "${#uuid}" = 32 ] || stop IDENTITY_INVALID
[ -d /data/local ] && [ ! -L /data/local ] || stop DATA_LOCAL_UNSAFE
[ ! -L "$DIR" ] || stop TEST_DIRECTORY_UNSAFE
created=0
if [ -e "$DIR" ]; then
 [ -d "$DIR" ] && [ "$("$BB" stat -c '%u:%g:%a' "$DIR")" = '0:0:700' ] || stop TEST_DIRECTORY_UNSAFE
else
 "$BB" mkdir -m 0700 "$DIR" || stop TEST_DIRECTORY_CREATE_FAILED
 created=1
fi
if [ -e "$FILE" ] || [ -L "$FILE" ] || [ -e "$STAMP" ] || [ -L "$STAMP" ]; then
 regular "$FILE" && regular "$STAMP" || stop TEST_EXISTING_STATE_UNSAFE
 [ "$("$BB" wc -l < "$STAMP")" = 2 ] || stop TEST_STAMP_INVALID
 first=$("$BB" sed -n '1p' "$STAMP")
 [ "${#first}" = 36 ] && [ "$("$BB" sed -n '2p' "$STAMP")" = "$uuid" ] || stop TEST_FILESYSTEM_CHANGED
 size=$("$BB" wc -c < "$FILE")
 hash=$("$BB" sha256sum "$FILE"); hash=${hash%% *}
 [ "$size" = 4120 ] && [ "$hash" = "$EXPECT" ] || stop TEST_FILE_MISMATCH
 [ "$first" != "$boot" ] || stop TEST_FILE_PRESENT_SAME_BOOT
 say TEST_FILE_PERSISTED_VERIFIED
 say XOOM_STORAGE_WRITE_TEST_END
 exit 0
fi
[ "$created" = 1 ] || stop TEST_DIRECTORY_EXISTS_WITHOUT_TRANSACTION
# Exclusive files; a partial transaction blocks the next run rather than retrying.
set -C
"$BB" printf '%s\n%s\n' "$boot" "$uuid" > "$STAMP" || stop TEST_STAMP_CREATE_FAILED
# Build the complete fixed payload in RAM before the exclusive target write.
"$BB" printf 'XOOM_STORAGE_PERSIST_V1\n' > /run/persist-payload || stop RAM_PAYLOAD_FAILED
"$BB" dd if=/dev/zero bs=4096 count=1 2>/dev/null | "$BB" tr '\000' 'A' >> /run/persist-payload || stop RAM_PAYLOAD_FAILED
[ "$("$BB" wc -c < /run/persist-payload)" = 4120 ] || stop RAM_PAYLOAD_SIZE
"$BB" cat /run/persist-payload > "$FILE" || stop TEST_FILE_CREATE_FAILED
set +C
"$BB" sync || stop TEST_SYNC_FAILED
regular "$FILE" && regular "$STAMP" || stop TEST_FILE_METADATA_FAILED
hash=$("$BB" sha256sum "$FILE"); hash=${hash%% *}
[ "$hash" = "$EXPECT" ] || stop TEST_WRITE_MISMATCH
say TEST_WRITE_OK_REBOOT_REQUIRED
say XOOM_STORAGE_WRITE_TEST_END
