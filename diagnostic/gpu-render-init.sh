#!/bin/busybox sh
# RAM-only bootstrap; original Android init supplies the bionic property FD.
export PATH=/bin:/system/bin
export LD_LIBRARY_PATH=/system/lib
umask 022
fail() {
 echo "XOOM_GPU_BOOTSTRAP_FAILED_$1" > /dev/kmsg
 while :; do /bin/busybox sleep 5; done
}
/bin/busybox mount -t proc proc /proc || fail proc
/bin/busybox mount -t sysfs sysfs /sys || fail sysfs
/bin/busybox mount -t devtmpfs devtmpfs /dev || fail dev
/bin/busybox mkdir -p /dev/pts /run /tmp /data /cache || fail dirs
/bin/busybox mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs /run || fail run
/bin/busybox mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /tmp || fail tmp
/bin/busybox mount -t tmpfs -o mode=0771,nosuid,nodev tmpfs /data || fail data
/bin/busybox mount -t tmpfs -o mode=0770,nosuid,nodev tmpfs /cache || fail cache
/bin/busybox mount -t devpts devpts /dev/pts || fail pts
/bin/busybox mount -t debugfs debugfs /sys/kernel/debug
/bin/busybox sh /bin/usb-report-loop > /run/usb-loop-errors.txt 2>&1 &
exec /init.android
