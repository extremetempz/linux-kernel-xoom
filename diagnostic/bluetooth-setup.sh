#!/bin/busybox sh
# Awake-only Bluetooth preparation. Never unblocks radio or attaches HCI.
# UART, power and firmware are controlled by the existing Android vendor HAL.
LOG=/run/xoom-bluetooth-setup.log
exec > "$LOG" 2>&1
BB=/bin/busybox
for attempt in 1 2 3 4 5 6 7 8 9 10; do
 [ -c /dev/ttyHS2 ] && break
 "$BB" sleep 1
done
[ -c /dev/ttyHS2 ] || { echo FAILED_uart_missing; exit 1; }
found=
for rf in /sys/class/rfkill/rfkill*; do
 [ -r "$rf/type" ] || continue
 [ "$("$BB" cat "$rf/type")" = bluetooth ] || continue
 # Do not assume rfkill0: bcmdhd may register Wi-Fi before this device.
 [ "$("$BB" cat "$rf/name")" = 'bcm4329 Bluetooth' ] || continue
 "$BB" chown 1002:1002 "$rf/state" || exit 1
 "$BB" chmod 0660 "$rf/state" || exit 1
 found=1
 echo "rfkill=$rf state=$("$BB" cat "$rf/state")"
done
[ "$found" = 1 ] || { echo FAILED_rfkill_missing; exit 1; }
# Android bluetooth UID/GID 1002. No world-writable device or rfkill nodes.
"$BB" chown 1002:1002 /dev/ttyHS2 || exit 1
"$BB" chmod 0660 /dev/ttyHS2 || exit 1
[ -r /system/lib/hw/bluetooth.default.so ] || { echo FAILED_bluetooth_hal; exit 1; }
if [ ! -r /system/lib/libbt-vendor.so ] && [ ! -r /system/vendor/lib/libbt-vendor.so ]; then
 echo FAILED_vendor_library_missing
 exit 1
fi
[ -r /system/etc/firmware/bcm4329.hcd ] || { echo FAILED_firmware_missing; exit 1; }
address_path=$(/system/bin/getprop ro.bt.bdaddr_path 2>/dev/null)
if [ -n "$address_path" ] && [ ! -r "$address_path" ]; then
 echo WARN_factory_bdaddr_path_unavailable_identity_requires_validation
fi
echo READY_for_manual_Android_Bluetooth_toggle_NOT_hardware_validated
