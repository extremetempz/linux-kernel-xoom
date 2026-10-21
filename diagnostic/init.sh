#!/bin/busybox sh
# Virtual filesystems only. Never mount an Android block device.
export PATH=/bin:/system/bin
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t devtmpfs devtmpfs /dev
/bin/busybox mkdir -p /dev/pts /run /tmp
/bin/busybox mount -t tmpfs tmpfs /run
/bin/busybox mount -t tmpfs tmpfs /tmp
/bin/busybox mount -t devpts devpts /dev/pts
/bin/busybox mount -t debugfs debugfs /sys/kernel/debug
# No unsolicited output: the host sets raw mode before requesting a report.
while :; do
 if [ -c /dev/ttyGS0 ]; then
  /bin/busybox sh /bin/diagnostic-server < /dev/ttyGS0 > /dev/ttyGS0 2>/run/diagnostic-server-errors.txt
 fi
 /bin/busybox sleep 1
done
