#!/bin/busybox sh
# Experimental image-30 entry point; package only with prepare-android44.py.
# PID1 remains this process through bootstrap and exec of the original init.
export PATH=/bin:/system/bin:/system/xbin
export LD_LIBRARY_PATH=/system/lib
umask 022
fail() {
 echo "XOOM_ANDROID44_EARLY_FAILED_$1" > /dev/kmsg
 while :; do /bin/busybox sleep 5; done
}
/bin/busybox mount -t proc proc /proc || fail proc
/bin/busybox mount -t sysfs sysfs /sys || fail sysfs
/bin/busybox mount -t devtmpfs devtmpfs /dev || fail devtmpfs
/bin/busybox mkdir -p /run /tmp /dev/pts || fail directories
/bin/busybox mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs /run || fail ram_run
/bin/busybox mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /tmp || fail ram_tmp
/bin/busybox mount -t devpts devpts /dev/pts || fail devpts
/bin/busybox mount -t debugfs debugfs /sys/kernel/debug
# Only the retained-console test profile mounts pstore. The ordinary RAM
# runtime deliberately filters the original ROM's pstore mount commands.
# Read-only VFS: collecting evidence cannot erase previous records.
if [ -e /proc/device-tree/motorola,wingray-pstore-test ]; then
 /bin/busybox mount -t pstore -o ro,nosuid,nodev,noexec pstore /sys/fs/pstore > /run/pstore-mount.txt 2>&1
 result=$?
 echo "PSTORE_MOUNT_RC $result" >> /run/pstore-mount.txt
 echo "XOOM_PSTORE_BOOT $(/bin/busybox cat /proc/sys/kernel/random/boot_id) mount_rc=$result" > /dev/kmsg
 # A multi-block known payload checks more than the UUID's 36 bytes. This
 # is a harmless console write, not a deliberate panic/reset or raw RAM poke.
 if [ -e /proc/device-tree/motorola,wingray-pstore-ecc-test ]; then
  boot_id=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
  pattern=
  for part in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
   pattern=${pattern}0123456789abcdef
  done
  digest=$(printf '%s' "$boot_id $pattern" | /bin/busybox sha256sum)
  digest=${digest%% *}
  printf 'XOOM_PSTORE_PROBE_V1 %s %s %s\n' "$boot_id" "$pattern" "$digest" > /run/pstore-probe.txt
  /bin/busybox cat /run/pstore-probe.txt > /dev/kmsg
 fi
fi
/bin/busybox sh /bin/usb-report-loop > /run/usb-loop-errors.txt 2>&1 &
exec /bin/busybox sh /bin/android44-bootstrap
