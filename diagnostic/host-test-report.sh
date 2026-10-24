#!/bin/busybox sh
/bin/busybox printf 'XOOM_HOST_ONLY_REPORT_BEGIN\n'
/bin/busybox ls -l /dev/nvmap /dev/nvhost* 2>/dev/null
/bin/busybox cat /proc/interrupts /proc/iomem
for field in /sys/bus/nvhost/devices/host1x/acm/*; do
 [ -r "$field" ] || continue
 echo "$field"
 /bin/busybox cat "$field" 2>/dev/null
done
/bin/busybox printf 'XOOM_HOST_ONLY_REPORT_END\n'
