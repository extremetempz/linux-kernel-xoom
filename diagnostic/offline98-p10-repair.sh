#!/bin/busybox sh
# Invoked only by the fixed REPAIR_P10_CONFIRM serial command.
exec </dev/ttyGS0 >/dev/ttyGS0 2>&1
echo XOOM_REPAIR_P10_BEGIN
[ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p10/ro)" = 1 ] || { echo XOOM_REPAIR_REFUSED_NOT_RO; exit 1; }
/bin/storage-policy || { echo XOOM_REPAIR_POLICY_FAILED; exit 2; }
[ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p10/ro)" = 0 ] || { echo XOOM_REPAIR_P10_NOT_RW; exit 3; }
[ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p9/ro)" = 1 ] || { echo XOOM_REPAIR_CACHE_NOT_RO; exit 4; }
[ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p8/ro)" = 1 ] || { echo XOOM_REPAIR_SYSTEM_NOT_RO; exit 5; }
[ "$(/bin/busybox cat /sys/block/mmcblk0/ro)" = 1 ] || { echo XOOM_REPAIR_DISK_NOT_RO; exit 6; }
/bin/busybox grep -q ' /data ' /proc/mounts && { echo XOOM_REPAIR_DATA_MOUNTED; exit 7; }
/bin/busybox grep -q ' /cache ' /proc/mounts && { echo XOOM_REPAIR_CACHE_MOUNTED; exit 8; }
echo XOOM_REPAIR_P10_RW_CACHE_SYSTEM_DISK_RO
/run/e2fsck -f /dev/mmcblk0p10
rc=$?
/bin/busybox sync
echo "XOOM_REPAIR_E2FSCK_EXIT $rc"
echo XOOM_REPAIR_REBOOT_REQUIRED_FOR_RO
while :; do /bin/busybox sleep 5; done
