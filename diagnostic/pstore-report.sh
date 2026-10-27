#!/bin/busybox sh
# Fixed read-only pstore/previous-console snapshot. No shell input is evaluated.
echo XOOM_PSTORE_REPORT_V1
echo "UPTIME $(/bin/busybox cut -d' ' -f1 /proc/uptime 2>/dev/null)"
echo "CURRENT_BOOT_ID $(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>/dev/null)"
if /bin/busybox awk '$2=="/sys/fs/pstore" && $3=="pstore" {found=1} END {exit !found}' /proc/mounts; then
 echo PSTORE_MOUNTED_yes
else
 echo PSTORE_MOUNTED_no
fi
[ ! -r /run/pstore-mount.txt ] || /bin/busybox cat /run/pstore-mount.txt
bound=0
for driver in /sys/bus/platform/drivers/ramoops/*.ramoops; do
 [ ! -L "$driver" ] || { echo "RAMOOPS_BOUND $driver"; bound=1; }
done
[ "$bound" -eq 1 ] || echo RAMOOPS_BACKEND_UNBOUND
for param in mem_address mem_size record_size console_size pmsg_size; do
 file=/sys/module/ramoops/parameters/$param
 [ ! -r "$file" ] || echo "RAMOOPS_PARAM $param $(/bin/busybox cat "$file")"
done
echo PSTORE_DIR
/bin/busybox ls -la /sys/fs/pstore 2>&1
budget=1572864
count=0
for f in /sys/fs/pstore/*; do
 [ -f "$f" ] || continue
 count=$((count + 1))
 [ "$count" -le 16 ] || { echo PSTORE_TRUNCATED_FILE_COUNT; break; }
 [ "$budget" -gt 0 ] || { echo PSTORE_TRUNCATED_TOTAL_CAP; break; }
 size=$(/bin/busybox wc -c < "$f")
 case "$size" in ''|*[!0-9]*) echo "PSTORE_SIZE_ERROR $f"; continue ;; esac
 take=$size
 [ "$take" -le "$budget" ] || take=$budget
 echo "PSTORE_FILE $f"
 echo "PSTORE_BYTES original=$size captured=$take"
 [ "$take" -eq "$size" ] || echo PSTORE_TRUNCATED_TAIL
 /bin/busybox tail -c "$take" "$f" 2>&1
 budget=$((budget - take))
 echo PSTORE_FILE_END
done
echo PSTORE_CONSOLE
echo PSTORE_CONSOLE_INCLUDED_IN_FILE_LOOP
echo LAST_KMSG
[ ! -r /proc/last_kmsg ] || /bin/busybox tail -c 131072 /proc/last_kmsg 2>&1
echo DMESG_TAIL
/bin/busybox dmesg 2>&1 | /bin/busybox tail -160 | /bin/busybox tail -c 131072
echo XOOM_PSTORE_REPORT_END
