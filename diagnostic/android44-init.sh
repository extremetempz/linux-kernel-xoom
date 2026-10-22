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
/bin/busybox sh /bin/usb-report-loop > /run/usb-loop-errors.txt 2>&1 &
exec /bin/busybox sh /bin/android44-bootstrap
