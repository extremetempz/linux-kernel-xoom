#!/bin/busybox sh
echo XOOM_NVMAP_RESOURCE_REPORT_BEGIN
/bin/busybox cat /proc/iomem
/bin/busybox ls -l /dev/nvmap
for heap in /sys/devices/platform/*nvmap*/misc/nvmap/heap-*; do
 [ -d "$heap" ] || continue
 echo "$heap"
 for field in name base total_size; do
  echo "$field"
  /bin/busybox cat "$heap/$field"
 done
done
/bin/busybox cat /run/nvmap-allocator-result.txt
# These checks are evidence of exclusion, not a request to activate an engine.
/bin/busybox ls /dev/nvhost* /dev/graphics/fb* 2>/dev/null
echo XOOM_NVMAP_RESOURCE_REPORT_END
