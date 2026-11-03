#!/bin/busybox sh
# Only explicit confirmed serial transaction invokes this script.
BB=/bin/busybox
exec </dev/ttyGS0 >/dev/ttyGS0 2>&1
[ ! -e /run/cache99-attempted ] || exit 1
$BB touch /run/cache99-attempted || exit 1
/bin/cache99-preflight || exit 1
released=0
cleanup() {
 [ "$released" = 1 ] || return
 echo CACHE99_RELOCK_BEGIN
 cleanup_failed=0
 $BB timeout -s KILL 30 $BB sync || { echo CACHE99_SYNC_FAILED; cleanup_failed=1; }
 if /bin/cache99-lock && [ "$($BB cat /sys/block/mmcblk0/mmcblk0p9/ro)" = 1 ]; then
  echo CACHE99_RELOCKED_RO
 else echo CACHE99_RELOCK_FAILED_DO_NOT_BOOT_ANDROID; cleanup_failed=1; fi
 for n in 1 2 3 4 5 6 7 8 9 10; do
  [ "$($BB cat /sys/block/mmcblk0/mmcblk0p$n/ro)" = 1 ] || cleanup_failed=1
 done
 [ "$($BB cat /sys/block/mmcblk0/ro)" = 1 ] || cleanup_failed=1
 return "$cleanup_failed"
}
trap cleanup EXIT
trap 'exit 2' HUP INT TERM
# Cleanup also runs if release returns failure after an uncertain ioctl.
released=1
/bin/cache99-release || exit 1
[ "$($BB cat /sys/block/mmcblk0/mmcblk0p9/ro)" = 0 ] || exit 1
for n in 1 2 3 4 5 6 7 8 10; do
 [ "$($BB cat /sys/block/mmcblk0/mmcblk0p$n/ro)" = 1 ] || exit 1
done
[ "$($BB cat /sys/block/mmcblk0/ro)" = 1 ] || exit 1
echo CACHE99_P9_ONLY_RW_INTERACTIVE_CHECKER
# No -y/-p; operator accepts only the reviewed bitmap-padding correction.
/run/e2fsck -f -E fixes_only,nodiscard /dev/mmcblk0p9
rc=$?
echo "CACHE99_REPAIR_EXIT $rc"
cleanup || exit 1
released=0
[ "$($BB cat /sys/block/mmcblk0/mmcblk0p9/ro)" = 1 ] || exit 1
case "$rc" in 0|1) :;; *) echo CACHE99_REPAIR_FAILED; exit 1;; esac
/run/e2fsck -f -n -E no_optimize_extents /dev/mmcblk0p9
check=$?
echo "CACHE99_READONLY_RECHECK_EXIT $check"
$BB sha256sum /dev/mmcblk0p9
[ "$check" = 0 ] || exit 1
echo CACHE99_REPAIR_COMPLETE_REQUIRES_NEW_READONLY_BACKUP
