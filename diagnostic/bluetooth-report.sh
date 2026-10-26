#!/bin/busybox sh
# Bounded, read-only evidence. No HCI commands, unblocks or address writes.
BB=/bin/busybox
echo XOOM_BLUETOOTH_BEGIN
"$BB" head -c 4096 /run/xoom-bluetooth-setup.log 2>/dev/null
"$BB" ls -l /dev/ttyHS2 2>/dev/null
for rf in /sys/class/rfkill/rfkill*; do
 [ -r "$rf/type" ] || continue
 echo "RFKILL $rf"
 for name in type name state soft hard; do
  [ ! -r "$rf/$name" ] || { echo "$name:"; "$BB" head -c 128 "$rf/$name"; }
 done
done
for name in /system/lib/hw/bluetooth.default.so /system/lib/libbt-vendor.so /system/vendor/lib/libbt-vendor.so /system/etc/firmware/bcm4329.hcd /system/etc/bluetooth/bt_vendor.conf; do
 [ ! -r "$name" ] || "$BB" sha256sum "$name"
done
[ ! -r /system/etc/bluetooth/bt_vendor.conf ] || "$BB" head -c 2048 /system/etc/bluetooth/bt_vendor.conf
"$BB" head -c 4096 /proc/tty/driver/tegra_hsuart 2>/dev/null
"$BB" timeout -s KILL 3 /system/bin/dumpsys bluetooth_manager 2>&1 | "$BB" head -c 12288
echo XOOM_BLUETOOTH_END
