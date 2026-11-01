#!/bin/busybox sh
# Controlled persistent-file test. Writes ONLY the dedicated test directory.
# First boot creates the fixed payload; later boots verify it without rewriting.
OUT=/run/android44-storage-write-test.txt
DIR=/data/local/xoom-storage-test
FILE=$DIR/persistent-v1.bin
EXPECT=4f5a76d96d52a7902acb25f86971d101fc9fae1d7d97039fb6f0fbbb0a7e13ee
say() { echo "$@"; echo "$@" >> "$OUT"; }
: > "$OUT"
say XOOM_STORAGE_WRITE_TEST_BEGIN
say "BOOT_ID $(/bin/busybox cat /proc/sys/kernel/random/boot_id)"
say "UPTIME $(/bin/busybox cat /proc/uptime)"
say "DATA_MOUNT $(/bin/busybox awk '$2=="/data"{print $1" "$3" "$4}' /proc/mounts)"
say "DATA_RO $(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p10/ro)"
if [ ! -d /data/local ] || [ -L /data/local ]; then
 say DATA_LOCAL_MISSING
 say XOOM_STORAGE_WRITE_TEST_END
 exit 1
fi
if [ -e "$DIR" ] && { [ ! -d "$DIR" ] || [ -L "$DIR" ]; }; then
 say TEST_DIRECTORY_UNSAFE
 say XOOM_STORAGE_WRITE_TEST_END
 exit 1
fi
if [ ! -e "$DIR" ]; then
 /bin/busybox mkdir -m 0700 "$DIR" || { say TEST_DIRECTORY_CREATE_FAILED; exit 1; }
 /bin/busybox chown 0:0 "$DIR"
 say TEST_DIRECTORY_CREATED
fi
if [ -e "$FILE" ] || [ -L "$FILE" ]; then
 [ -f "$FILE" ] && [ ! -L "$FILE" ] || { say TEST_FILE_UNSAFE; exit 1; }
 size=$(/bin/busybox wc -c < "$FILE")
 hash=$(/bin/busybox sha256sum "$FILE")
 hash=${hash%% *}
 say "TEST_FILE_PRESENT size=$size sha256=$hash"
 [ "$size" = 4120 ] && [ "$hash" = "$EXPECT" ] || { say TEST_FILE_MISMATCH; exit 1; }
 say TEST_FILE_PERSISTED_VERIFIED
 say XOOM_STORAGE_WRITE_TEST_END
 exit 0
fi
# Create the file without overwriting anything, with a fixed known payload.
set -C
/bin/busybox printf 'XOOM_STORAGE_PERSIST_V1\n' > "$FILE" || { say TEST_FILE_CREATE_FAILED; exit 1; }
/bin/busybox dd if=/dev/zero bs=4096 count=1 2>/dev/null | /bin/busybox tr '\000' 'A' >> "$FILE" || { say TEST_PAYLOAD_FAILED; exit 1; }
set +C
/bin/busybox chown 0:0 "$FILE"
/bin/busybox chmod 0600 "$FILE"
sync
sync
size=$(/bin/busybox wc -c < "$FILE")
hash=$(/bin/busybox sha256sum "$FILE")
hash=${hash%% *}
say "TEST_FILE_WRITTEN size=$size sha256=$hash"
[ "$size" = 4120 ] && [ "$hash" = "$EXPECT" ] || { say TEST_WRITE_MISMATCH; exit 1; }
say TEST_WRITE_OK_REBOOT_REQUIRED
say XOOM_STORAGE_WRITE_TEST_END
exit 0
