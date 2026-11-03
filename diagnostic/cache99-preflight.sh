#!/bin/busybox sh
# Read-only, repeatable checks before any release. No physical fsck here.
BB=/bin/busybox
fail() { echo "CACHE99_PREFLIGHT_FAILED_$1"; exit 1; }
[ "$( $BB cat /run/offline97-state )" = passed ] || fail ramtest
[ -e /sys/firmware/devicetree/base/motorola,wingray-cache-repair99 ] || fail profile
[ "$($BB cat /sys/block/mmcblk0/size)" = 62521344 ] || fail disk
[ "$($BB cat /sys/block/mmcblk0/ro)" = 1 ] || fail disk_ro
while read n start size; do
 path=/sys/block/mmcblk0/mmcblk0p$n
 [ "$($BB cat "$path/start")" = "$start" ] || fail start
 [ "$($BB cat "$path/size")" = "$size" ] || fail size
 [ "$($BB cat "$path/ro")" = 1 ] || fail partition_ro
 [ -z "$($BB ls -A "$path/holders")" ] || fail holders
 [ "$($BB stat -c '%t:%T' /dev/mmcblk0p$n)" = "b3:$($BB printf '%x' "$n")" ] || fail device_identity
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
[ -z "$($BB ls -A /sys/block/mmcblk0/holders)" ] || fail disk_holders
while read source target type rest; do
 case "$type" in rootfs|proc|sysfs|devtmpfs|tmpfs|devpts) :;; *) fail nonvirtual_mount;; esac
done < /proc/mounts
$BB awk '$3 ~ /^179:/ {bad=1} END {exit bad}' /proc/self/mountinfo || fail emmc_mount
[ "$($BB wc -l < /proc/swaps)" = 1 ] || fail swap
# No storage gadget in this RAM-only profile, nor competing Android/recovery processes.
[ ! -d /sys/module/g_mass_storage ] || fail storage_export
hash=$($BB sha256sum /dev/mmcblk0p9) || fail source_read
[ "${hash%% *}" = 7053be21ae7e7c627aa829eafc97501cd5ceae2063f56177a4ce28488b3e4aef ] || fail original_hash
# Sync remains read-only here and completes any outstanding reads before arming.
$BB timeout -s KILL 30 $BB sync || fail sync
echo CACHE99_PREFLIGHT_PASSED_P9_RO_ALL_OTHERS_RO
