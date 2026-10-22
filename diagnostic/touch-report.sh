#!/bin/busybox sh
# Fixed read-only metadata and a five-second independent evdev observation.
echo XOOM_TOUCH_BEGIN
if [ "$(/bin/busybox uname -r)" != 4.4.147-wingray-android44-touch ]; then
 echo XOOM_TOUCH_DENIED_RELEASE
 echo XOOM_TOUCH_END
 exit 0
fi
if ! /bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx motorola,wingray; then
 echo XOOM_TOUCH_DENIED_BOARD
 echo XOOM_TOUCH_END
 exit 0
fi
echo XOOM_TOUCH_I2C_METADATA_BEGIN
/bin/busybox ls -ld /sys/bus/i2c/devices/0-005b/driver 2>&1 | /bin/busybox head -c 512
echo
for attr in name modalias fw_version hw_version; do
 path="/sys/bus/i2c/devices/0-005b/$attr"
 [ ! -r "$path" ] || { echo "XOOM_TOUCH_I2C $attr"; /bin/busybox head -c 256 "$path"; echo; }
done
echo XOOM_TOUCH_I2C_METADATA_END
echo XOOM_TOUCH_INPUT_METADATA_BEGIN
# Bound to the fixed 16-node whitelist used by the native reader.
for index in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
 path="/sys/class/input/event$index/device"
 [ -d "$path" ] || continue
 [ "$(/bin/busybox head -c 128 "$path/name")" = "Atmel maXTouch Touchscreen" ] || continue
 echo "XOOM_TOUCH_INPUT event$index"
 for attr in name phys properties capabilities/ev capabilities/key capabilities/abs; do
  [ ! -r "$path/$attr" ] || { echo "$attr"; /bin/busybox head -c 256 "$path/$attr"; echo; }
 done
 break
done
/bin/busybox head -c 2048 /proc/bus/input/devices
echo
echo XOOM_TOUCH_INPUT_METADATA_END
echo XOOM_TOUCH_INTERRUPTS_BEFORE
/bin/busybox head -c 4096 /proc/interrupts
echo
echo XOOM_TOUCH_SAMPLE_BEGIN
if [ -x /bin/touch-events ]; then
 /bin/touch-events
 echo "XOOM_TOUCH_SAMPLE_EXIT $?"
else
 echo XOOM_TOUCH_SAMPLE_MISSING
fi
echo XOOM_TOUCH_SAMPLE_END
echo XOOM_TOUCH_INTERRUPTS_AFTER
/bin/busybox head -c 4096 /proc/interrupts
echo
echo XOOM_TOUCH_END
