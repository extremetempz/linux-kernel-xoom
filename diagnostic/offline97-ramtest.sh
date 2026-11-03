#!/bin/busybox sh
# Writable arguments are fixed regular RAM files only. No physical fsck command.
set -u
fail() { echo "OFFLINE97_RAMTEST_FAILED_$1"; exit 1; }
/bin/busybox uname -r
/run/e2fsck -V || fail version
[ "$(/bin/busybox cat /sys/block/mmcblk0/size)" = 62521344 ] || fail disk_size
[ "$(/bin/busybox cat /sys/block/mmcblk0/ro)" = 1 ] || fail disk_ro
while read number start size; do
 path=/sys/block/mmcblk0/mmcblk0p$number
 [ "$(/bin/busybox cat "$path/start")" = "$start" ] || fail start
 [ "$(/bin/busybox cat "$path/size")" = "$size" ] || fail size
 [ "$(/bin/busybox cat "$path/ro")" = 1 ] || fail partition_ro
done <<'GEOMETRY'
1 51200 6144
2 57344 4096
3 61440 4096
4 65536 8192
5 73728 4096
6 77824 24576
7 102400 16384
8 118784 2097152
9 2215936 1048576
10 3264512 59247616
GEOMETRY
# Refuse any non-virtual mount; only these five types are created by PID1.
while read source target type rest; do
 case "$type" in rootfs|proc|sysfs|devtmpfs|tmpfs|devpts) :;; *) fail unexpected_mount;; esac
done < /proc/mounts
/bin/busybox xz -dc /fixtures/clean.img.xz > /run/clean.img || fail decompress_clean
/bin/busybox xz -dc /fixtures/counter.img.xz > /run/counter.img || fail decompress_counter
[ -f /run/clean.img ] && [ ! -L /run/clean.img ] || fail fixture_type
[ -f /run/counter.img ] && [ ! -L /run/counter.img ] || fail fixture_type
/run/e2fsck -f -n -E no_optimize_extents /run/clean.img
rc=$?; echo "CLEAN_CHECK_EXIT $rc"; [ "$rc" = 0 ] || fail clean
/run/e2fsck -f -n -E no_optimize_extents /run/counter.img
rc=$?; echo "COUNTER_BEFORE_EXIT $rc"; [ "$rc" = 4 ] || fail expected_counter_error
/run/e2fsck -f -p -E fixes_only,nodiscard /run/counter.img
rc=$?; echo "COUNTER_REPAIR_EXIT $rc"; [ "$rc" = 1 ] || fail counter_repair
/run/e2fsck -f -n -E no_optimize_extents /run/counter.img
rc=$?; echo "COUNTER_AFTER_EXIT $rc"; [ "$rc" = 0 ] || fail counter_after
echo OFFLINE97_RAMTEST_PASSED_PHYSICAL_WRITES_DISABLED
