#!/bin/busybox sh
# Validation-only report. No Android, physical mounts or repair commands.
echo "XOOM_FRESH_REPORT_V2 $1"
echo XOOM_OFFLINE97_BEGIN
echo 'scope=cache99_manual_gate android=absent twrp=absent mass_storage=absent physical_repair=not_automatic'
echo 'pid1=offline97-init mounts=virtual_only writable_fixtures=ram_only'
/bin/busybox cat /run/offline97-state /run/offline97-ramtest.txt 2>/dev/null
/bin/busybox cat /run/checker-chunks.txt /run/checker-copy.txt /run/chunks-manifest.txt /run/chunks-list.txt 2>/dev/null
/bin/busybox cat /proc/sys/vm/mmap_min_addr 2>/dev/null | /bin/busybox sed "s/^/mmap_min_addr=/"
/bin/busybox df -h /run 2>/dev/null
/bin/busybox cat /run/cache99-preflight.txt 2>/dev/null
echo XOOM_OFFLINE97_END
echo XOOM_CACHE99_POLICY_BEGIN
if [ -e /run/cache99-attempted ]; then echo CACHE99_ATTEMPTED 1; else echo CACHE99_ATTEMPTED 0; fi
echo "CACHE99_RAM_STATE $(/bin/busybox cat /run/offline97-state)"
echo XOOM_MOUNTS_BEGIN
/bin/busybox cat /proc/mounts
echo XOOM_MOUNTS_END
echo "XOOM_DISK mmcblk0 $(/bin/busybox cat /sys/block/mmcblk0/size) $(/bin/busybox cat /sys/block/mmcblk0/ro)"
for n in 1 2 3 4 5 6 7 8 9 10; do
 path=/sys/block/mmcblk0/mmcblk0p$n
 echo "XOOM_PART mmcblk0p$n $(/bin/busybox cat "$path/start") $(/bin/busybox cat "$path/size")"
 echo "CACHE99_RO mmcblk0p$n $(/bin/busybox cat "$path/ro")"
done
echo XOOM_CACHE99_POLICY_END
echo "XOOM_FRESH_REPORT_DONE $1"
