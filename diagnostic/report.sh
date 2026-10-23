#!/bin/busybox sh
# All reads below are virtual metadata or kernel logs. No block I/O commands,
# filesystem mounts, regulator changes or arbitrary USB-supplied commands.
nonce=$1
/bin/busybox printf 'XOOM_FRESH_REPORT_V2 %s\n' "$nonce"
/bin/busybox printf 'XOOM_UPTIME_START '
/bin/busybox cat /proc/uptime
# Wait for disk AND partition registration, rather than cache a 0.55s snapshot.
waited=0
while [ "$waited" -lt 20 ]; do
 complete=1
 for number in 1 2 3 4 5 6 7 8 9 10; do
  [ -d "/sys/block/mmcblk0/mmcblk0p$number" ] || complete=0
 done
 [ "$complete" -eq 1 ] && break
 /bin/busybox sleep 1
 waited=$((waited + 1))
done
/bin/busybox printf 'XOOM_STORAGE_WAIT_SECONDS %s\n' "$waited"
/bin/busybox printf 'XOOM_UPTIME_SNAPSHOT '
/bin/busybox cat /proc/uptime
/bin/busybox uname -a
/bin/busybox printf 'XOOM_CMDLINE_BEGIN\n'
/bin/busybox cat /proc/cmdline
/bin/busybox printf 'XOOM_CMDLINE_END\nXOOM_PARTITIONS_BEGIN\n'
/bin/busybox cat /proc/partitions
/bin/busybox printf 'XOOM_PARTITIONS_END\nXOOM_MOUNTS_BEGIN\n'
/bin/busybox cat /proc/mounts
/bin/busybox printf 'XOOM_MOUNTS_END\n'
if [ -d /sys/block/mmcblk0 ]; then
 size=$(/bin/busybox cat /sys/block/mmcblk0/size)
 ro=$(/bin/busybox cat /sys/block/mmcblk0/ro)
 /bin/busybox printf 'XOOM_DISK mmcblk0 %s %s\n' "$size" "$ro"
 for number in 1 2 3 4 5 6 7 8 9 10; do
  part="/sys/block/mmcblk0/mmcblk0p$number"
  if [ -d "$part" ]; then
   start=$(/bin/busybox cat "$part/start")
   size=$(/bin/busybox cat "$part/size")
   /bin/busybox printf 'XOOM_PART mmcblk0p%s %s %s\n' "$number" "$start" "$size"
  else
   /bin/busybox printf 'XOOM_PART_MISSING mmcblk0p%s\n' "$number"
  fi
 done
else
 /bin/busybox printf 'XOOM_DISK_MISSING mmcblk0\n'
fi
/bin/busybox printf 'XOOM_MMC_HOSTS_BEGIN\n'
/bin/busybox ls -l /sys/class/mmc_host /sys/bus/mmc/devices
for card in /sys/bus/mmc/devices/*; do
 [ -d "$card" ] || continue
 /bin/busybox printf 'XOOM_MMC_CARD %s\n' "$card"
 for name in type name state; do
  [ -r "$card/$name" ] || continue
  /bin/busybox printf '%s=' "$name"
  /bin/busybox cat "$card/$name"
 done
done
/bin/busybox printf 'XOOM_MMC_HOSTS_END\nXOOM_INTERRUPTS_BEGIN\n'
/bin/busybox cat /proc/interrupts
/bin/busybox printf 'XOOM_INTERRUPTS_END\nXOOM_GPIO_BEGIN\n'
[ ! -r /sys/kernel/debug/gpio ] || /bin/busybox cat /sys/kernel/debug/gpio
[ ! -r /sys/kernel/debug/tegra_gpio ] || /bin/busybox cat /sys/kernel/debug/tegra_gpio
/bin/busybox printf 'XOOM_GPIO_END\n'
if [ -x /bin/panelbus-report ]; then
 /bin/busybox sh /bin/panelbus-report
fi
if [ -x /bin/display-report ]; then
 /bin/busybox sh /bin/display-report
fi
if [ -x /bin/android44-report ]; then
 /bin/busybox sh /bin/android44-report
fi
if [ -x /bin/touch-report ]; then
 /bin/busybox sh /bin/touch-report
fi
if [ -x /bin/soc-report ]; then
 /bin/busybox sh /bin/soc-report
fi
/bin/busybox printf 'XOOM_DMESG_BEGIN\n'
/bin/busybox dmesg | /bin/busybox tail -c 262144
/bin/busybox printf 'XOOM_DMESG_END\nXOOM_FRESH_REPORT_DONE %s\n' "$nonce"
