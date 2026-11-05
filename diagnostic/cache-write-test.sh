#!/bin/busybox sh
# Diagnostic: 64 MiB p9 cache write, fsync, sync, unmount. No Android.
exec </dev/ttyGS0 >/dev/ttyGS0 2>&1
BB=/bin/busybox
OUT=/data/xoom-cache-large-result
: > "$OUT" 2>/dev/null
say() { echo "$@"; echo "$@" >> "$OUT"; }
fail() { say "FAIL_$1"; $BB sync; while :; do $BB sleep 5; done; }
say CACHE_LARGE_BEGIN
[ "$($BB awk '$2=="/cache"{print $1" "$3}' /proc/mounts)" = '/dev/mmcblk0p9 ext4' ] || fail MOUNT
[ -f /cache/xoom-cache-large.bin ] && fail FILE_EXISTS
say "BOOT_ID $($BB cat /proc/sys/kernel/random/boot_id)"
file=/cache/xoom-cache-large.bin
$BB dd if=/dev/zero of="$file" bs=1M count=64 conv=fsync 2>/dev/null || fail DD
$BB sync || fail SYNC
size=$($BB wc -c < "$file")
say "SIZE $size"
[ "$size" = 67108864 ] || fail SIZE
say CACHE_LARGE_WRITE_OK_BEFORE_UMOUNT
$BB sync
$BB timeout -s KILL 30 $BB umount /cache
rc=$?
say "UMOUNT_RC $rc"
$BB sync
say CACHE_LARGE_END
while :; do $BB sleep 5; done
