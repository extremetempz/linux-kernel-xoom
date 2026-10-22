#!/bin/busybox sh
# DRAFT: incomplete Android image-30 integration; do not deploy directly.
# See docs/android44-lockscreen-checkpoint.md for missing generation and validation.
# PID1 remains this process through bootstrap and exec of the original init.
export PATH=/bin:/system/bin:/system/xbin
export LD_LIBRARY_PATH=/system/lib
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t devtmpfs devtmpfs /dev
/bin/busybox mkdir -p /run /tmp /dev/pts
/bin/busybox mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs /run
/bin/busybox mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /tmp
/bin/busybox mount -t devpts devpts /dev/pts
/bin/busybox mount -t debugfs debugfs /sys/kernel/debug
/bin/busybox sh /bin/usb-report-loop > /run/usb-loop-errors.txt 2>&1 &
exec /bin/busybox sh /bin/android44-bootstrap
