#!/bin/busybox sh
# Read-only metadata. The bound driver owns SMBus; never use forced i2c tools.
echo XOOM_DISPLAY_BEGIN
case "$(/bin/busybox uname -r)" in
 4.4.147-wingray-display|4.4.147-wingray-android44|4.4.147-wingray-android44-touch|4.4.147-wingray-android44-l2|4.4.147-wingray-android44-smp|4.4.147-wingray-android44-smp2|4.4.147-wingray-android44-smptrace) ;;
 *)
 echo XOOM_DISPLAY_DENIED_RELEASE
 echo XOOM_DISPLAY_END
 exit 0 ;;
esac
echo XOOM_PATTERN_RESULT_BEGIN
[ ! -r /run/display-pattern-result.txt ] || /bin/busybox cat /run/display-pattern-result.txt
echo XOOM_PATTERN_RESULT_END
echo XOOM_FB_BEGIN
/bin/busybox cat /proc/fb
for fb in /sys/class/graphics/fb[0-9]*; do
 [ -d "$fb" ] || continue
 echo "XOOM_FB $fb"
 for attr in name modes virtual_size bits_per_pixel stride blank; do
  [ -r "$fb/$attr" ] || continue
  /bin/busybox printf '%s=' "$attr"
  /bin/busybox cat "$fb/$attr"
 done
done
echo XOOM_FB_END
echo XOOM_DRM_BEGIN
for connector in /sys/class/drm/card0-*; do
 [ -d "$connector" ] || continue
 echo "XOOM_CONNECTOR $connector"
 for attr in status enabled modes dpms; do
  [ -r "$connector/$attr" ] || continue
  /bin/busybox printf '%s=' "$attr"
  /bin/busybox cat "$connector/$attr"
 done
done
echo XOOM_DRM_END
echo XOOM_BACKLIGHT_BEGIN
for attr in brightness actual_brightness max_brightness bl_power type; do
 path="/sys/class/backlight/lcd-backlight/$attr"
 [ -r "$path" ] || continue
 /bin/busybox printf '%s=' "$attr"
 /bin/busybox cat "$path"
done
/bin/busybox ls -l /sys/bus/i2c/devices/0-002c/driver
[ ! -r /sys/bus/i2c/devices/0-002c/wingray_registers ] || /bin/busybox cat /sys/bus/i2c/devices/0-002c/wingray_registers
echo XOOM_BACKLIGHT_END
echo XOOM_PANEL_REGULATORS_BEGIN
for rail in /sys/class/regulator/regulator.*; do
 [ -r "$rail/name" ] || continue
 [ "$(/bin/busybox cat "$rail/name")" = wingray-panel ] || continue
 for attr in name microvolts num_users state; do
  [ -r "$rail/$attr" ] || continue
  /bin/busybox printf '%s=' "$attr"
  /bin/busybox cat "$rail/$attr"
 done
done
echo XOOM_PANEL_REGULATORS_END
echo XOOM_CLOCKS_BEGIN
[ ! -r /sys/kernel/debug/clk/clk_summary ] || /bin/busybox cat /sys/kernel/debug/clk/clk_summary
echo XOOM_CLOCKS_END
echo XOOM_DISPLAY_END
