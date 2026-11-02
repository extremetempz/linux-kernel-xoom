#!/bin/busybox sh
# Read-only, bounded snapshot; no register tools, GPIO exports or sysfs writes.
echo XOOM_BATTERY_MONITOR_V1_BEGIN
/bin/busybox cat /proc/uptime
for supply in /sys/class/power_supply/*; do
 [ -d "$supply" ] || continue
 echo "SUPPLY ${supply##*/}"
 for prop in type present capacity status voltage_now current_now charge_counter energy_now power_now temp health online; do
  if [ -e "$supply/$prop" ]; then
   echo "PROPERTY $prop"
   /bin/busybox cat "$supply/$prop" 2>&1
   echo "READ_EXIT $?"
  fi
 done
done
echo XOOM_BATTERY_GPIO_INPUTS
[ ! -r /sys/kernel/debug/gpio ] || /bin/busybox grep -E 'wingray-stat|wingray-detect|chg_' /sys/kernel/debug/gpio
echo XOOM_BATTERY_INTERRUPTS
/bin/busybox grep -Ei 'owr|tegra_w1|cpcap' /proc/interrupts
echo XOOM_BATTERY_KERNEL_LOG
/bin/busybox dmesg | /bin/busybox grep -Ei 'ds2781|battery|charger|tegra_w1|1-wire|w1_|owr|i2c.*(error|fail|timeout)|CPCAP|nobody cared|Disabling IRQ' | /bin/busybox tail -100
# Android tools are called only when the inherited bootstrap verified system.
if [ -x /system/bin/dumpsys ]; then
 /bin/busybox timeout 8 /system/bin/dumpsys battery 2>&1
 /bin/busybox timeout 8 /system/bin/dumpsys batteryproperties 2>&1
 /bin/busybox timeout 8 /system/bin/logcat -d -v brief -t 160 2>&1 | /bin/busybox grep -Ei 'healthd|BatteryService|battery|charger'
fi
echo XOOM_BATTERY_MONITOR_V1_END
