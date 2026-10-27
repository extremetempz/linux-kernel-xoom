#!/bin/busybox sh
# Read only: no /dev/mem, register writes, GPIO exports, suspend or wake commands.
echo XOOM_DISPLAY_POWER_V1_BEGIN
/bin/busybox cat /proc/uptime
for file in /sys/power/state /sys/power/wakeup_count /sys/power/wake_lock /sys/power/mem_sleep /sys/devices/system/cpu/online /sys/devices/system/cpu/offline; do
 echo "FILE $file"
 [ ! -r "$file" ] || /bin/busybox head -c 4096 "$file"
done
for file in /sys/class/backlight/lcd-backlight/brightness /sys/class/backlight/lcd-backlight/actual_brightness /sys/class/backlight/lcd-backlight/bl_power /sys/class/graphics/fb0/blank /sys/class/graphics/fb0/state; do
 echo "FILE $file"
 [ ! -r "$file" ] || /bin/busybox head -c 512 "$file"
done
/bin/busybox grep -Ei 'cpcap|tegradc|display|mxt|owr|tegra_w1|bcmdhd|wlan' /proc/interrupts
for file in /sys/kernel/debug/wakeup_sources /sys/kernel/debug/suspend_stats /sys/kernel/debug/regulator/regulator_summary; do
 echo "FILE $file"
 [ ! -r "$file" ] || /bin/busybox head -c 8192 "$file"
done
# Existing debugfs only: never read raw PMC addresses while clocks may be off.
pmc_available=0
for file in /sys/kernel/debug/tegra_pmc/wake_status /sys/kernel/debug/pmc/wake_status; do
 if [ -r "$file" ]; then
  pmc_available=1
  /bin/busybox head -c 1024 "$file"
 fi
done
[ "$pmc_available" -eq 1 ] || echo PMC_WAKE_STATUS_UNAVAILABLE_NO_RAW_REGISTER_ACCESS
[ ! -x /bin/battery-report ] || /bin/battery-report
/bin/busybox dmesg | /bin/busybox grep -Ei 'Wingray (display|backlight|DC test|native mode)|lp855|suspend|resume|wakeup|CPCAP|nobody cared|Disabling IRQ' | /bin/busybox tail -120
if [ -x /system/bin/dumpsys ]; then
 /bin/busybox timeout 8 /system/bin/dumpsys power 2>&1
 /bin/busybox timeout 8 /system/bin/dumpsys display 2>&1
fi
echo XOOM_DISPLAY_POWER_V1_END
