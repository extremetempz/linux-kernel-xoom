#!/bin/busybox sh
# Invoked by the isolated init profile only, after init stops Android service classes.
BB=/bin/busybox
OUT=/run/android44-shutdown.txt
note() { echo "XOOM_SHUTDOWN_$*" >> "$OUT"; echo "XOOM_SHUTDOWN_$*" > /dev/kmsg; }
stop() { note "BLOCKED_$1"; exit 1; }
case "$#:$1" in 1:shutdown|1:reboot) mode=$1;; *) exit 1;; esac
[ -f /bin/clean-shutdown-enabled ] || exit 1
[ "$($BB id -u)" = 0 ] || exit 1
$BB mkdir /run/xoom-shutdown.lock 2>/dev/null || exit 1
note "BEGIN_$mode"
# No arbitrary command, force-unmount, lazy-unmount, fsck or policy release.
$BB timeout -s KILL 30 $BB sync || stop sync
note SYNCED
# Stop sdcard first through init class_stop; detach only actual emulated mounts.
targets=$($BB awk '$5 ~ /^\/storage\/emulated(\/[0-9]+)?$/ || $5 == "/mnt/shell/emulated" {print $5}' /proc/self/mountinfo | $BB sort -r)
for target in $targets; do
 $BB timeout -s KILL 10 $BB umount "$target" || stop emulated_unmount
done
for target in /cache /data; do
 line=$($BB awk -v t="$target" '$5==t {print $3" "$5}' /proc/self/mountinfo)
 [ -n "$line" ] || { [ "$target" = /cache ] && continue; stop data_missing; }
 case "$target:$line" in
  '/data:179:10 /data') :;;
  '/cache:179:9 /cache') [ -f /bin/storage-cache-approved ] || stop cache_unapproved;;
  /cache:0:*) :;;
  *) stop mount_identity;;
 esac
 note "QUIESCE_$target"
 if ! $BB timeout -s KILL 15 $BB umount "$target"; then
  $BB timeout -s KILL 15 $BB mount -o remount,ro "$target" || stop remount_readonly
 fi
done
# Check all remaining eMMC aliases, not just the /data and /cache paths.
$BB awk '$3 ~ /^179:/ {s=0; for(i=1;i<=NF;i++)if($i=="-")s=i;
 if(!s || $6 ~ /(^|,)rw(,|$)/ || $(s+3) ~ /(^|,)rw(,|$)/)bad=1}
 END {exit bad}' /proc/self/mountinfo || stop writable_alias
note FILESYSTEMS_READONLY_OR_UNMOUNTED
$BB timeout -s KILL 30 $BB sync || stop final_sync
volumes=/dev/mmcblk0p10
[ ! -f /bin/storage-cache-approved ] || volumes="$volumes /dev/mmcblk0p9"
for volume in $volumes; do
 state=$($BB dd if="$volume" bs=1 skip=1082 count=2 2>/dev/null | $BB od -An -v -tx1 | $BB tr -d ' \n')
 incompat=$($BB dd if="$volume" bs=1 skip=1120 count=1 2>/dev/null | $BB od -An -v -tx1 | $BB tr -d ' \n')
 [ "$state" = 0100 ] && [ "${#incompat}" = 2 ] || stop filesystem_not_clean
 [ $((0x$incompat & 4)) = 0 ] || stop filesystem_recovery_pending
done
note FILESYSTEM_CLEAN
# Property service belongs to init, not servicemanager; it remains alive.
/system/bin/setprop sys.xoom.shutdown_ready "$mode" || stop native_handoff
note "HANDOFF_$mode"
