#!/bin/busybox sh
# Fixed read-only pstore/previous-console snapshot. No shell input is evaluated.
echo XOOM_PSTORE_REPORT_V1
echo "UPTIME $(/bin/busybox cut -d' ' -f1 /proc/uptime 2>/dev/null)"
echo PSTORE_DIR
/bin/busybox ls -la /sys/fs/pstore 2>&1
for f in /sys/fs/pstore/*; do
 [ -f "$f" ] || continue
 echo "PSTORE_FILE $f"
 /bin/busybox cat "$f" 2>&1
 echo PSTORE_FILE_END
done
echo PSTORE_CONSOLE
[ ! -r /sys/fs/pstore/console-ramoops ] || /bin/busybox cat /sys/fs/pstore/console-ramoops 2>&1
echo LAST_KMSG
[ ! -r /proc/last_kmsg ] || /bin/busybox cat /proc/last_kmsg 2>&1
echo DMESG_TAIL
/bin/busybox dmesg 2>&1 | /bin/busybox tail -160
echo XOOM_PSTORE_REPORT_END
