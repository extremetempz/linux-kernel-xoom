#!/system/bin/sh
# Read-only PM snapshot; never mounts debugfs, writes state or changes wake IRQs.
BB=/bin/busybox
[ -x "$BB" ] || BB=busybox
read_file() {
    echo "PM_FILE $1"
    if [ -r "$1" ]; then "$BB" cat "$1"; else echo UNAVAILABLE; fi
}
echo PM_SNAPSHOT_BEGIN
for f in /proc/sys/kernel/random/boot_id /proc/uptime /sys/power/state /sys/power/pm_test /sys/power/wakeup_count /sys/power/wake_lock /proc/wakelocks /sys/kernel/debug/wakeup_sources /sys/kernel/debug/suspend_stats /proc/interrupts /sys/devices/system/cpu/online /sys/devices/system/cpu/offline /sys/class/graphics/fb0/blank /sys/class/graphics/fb0/state /sys/class/graphics/fb0/wingray_dc_test; do
    read_file "$f"
done
for d in /sys/class/backlight/* /sys/class/power_supply/*; do
    [ -d "$d" ] || continue
    for n in brightness actual_brightness bl_power capacity voltage_now current_now temp status online; do
        [ ! -e "$d/$n" ] || read_file "$d/$n"
    done
done
for f in /sys/bus/spi/devices/*/wingray_irq_status /sys/bus/spi/devices/*/wingray_wake_arm; do
    [ ! -e "$f" ] || read_file "$f"
done
# Register access through /dev/mem is deliberately excluded.
echo PMC_RAW_REGISTERS_NOT_READ
echo PM_KERNEL_LOG_BEGIN
"$BB" dmesg | "$BB" grep -E 'Wingray PM|PM:|suspend|resume|wakeup|WG_DC85|cpcap|ramoops' | "$BB" tail -n 250
echo PM_SNAPSHOT_END
