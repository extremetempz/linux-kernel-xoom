#!/bin/busybox sh
# Read-only metadata. The bound driver owns SMBus; never use forced i2c tools.
echo XOOM_DISPLAY_BEGIN
case "$(/bin/busybox uname -r)" in
 4.4.147-wingray-display|4.4.147-wingray-android44|4.4.147-wingray-android44-touch|4.4.147-wingray-android44-l2|4.4.147-wingray-android44-smp|4.4.147-wingray-android44-smp2|4.4.147-wingray-android44-smptrace|4.4.147-wingray-android44-gpu) ;;
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
/bin/busybox ls -l /sys/class/backlight
for attr in brightness actual_brightness max_brightness bl_power power type; do
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
echo XOOM_DC_BEGIN
/bin/busybox ls -l /sys/kernel/debug/tegradc.0 2>/dev/null
for attr in mode stats; do
 path="/sys/kernel/debug/tegradc.0/$attr"
 [ -r "$path" ] || continue
 echo "XOOM_DC $attr"
 /bin/busybox cat "$path"
done
if [ -r /sys/kernel/debug/tegradc.0/regs ]; then
 echo 'XOOM_DC regs'
 /bin/busybox head -c 32768 /sys/kernel/debug/tegradc.0/regs
 echo
fi
echo XOOM_DC_END
echo XOOM_SCREEN_AWAKE_BEGIN
[ ! -r /run/xoom-screen-awake.log ] || /bin/busybox cat /run/xoom-screen-awake.log
echo XOOM_SCREEN_AWAKE_END
echo XOOM_INPUT_DEVICES_BEGIN
[ ! -r /proc/bus/input/devices ] || /bin/busybox cat /proc/bus/input/devices
echo XOOM_INPUT_DEVICES_END
echo XOOM_NET_BEGIN
[ ! -d /sys/class/net ] || /bin/busybox ls /sys/class/net
[ ! -r /proc/net/dev ] || /bin/busybox cat /proc/net/dev
for interface in wlan0 wlan1; do
 [ ! -r "/sys/class/net/$interface/address" ] || { echo "$interface address:"; /bin/busybox cat "/sys/class/net/$interface/address"; }
done
[ ! -d /lib/firmware/brcm ] || /bin/busybox ls -l /lib/firmware/brcm
echo XOOM_NET_END
echo XOOM_WIFI_FILES_BEGIN
for directory in /system/etc/wifi /system/vendor/firmware /system/etc/firmware; do
 if [ -d "$directory" ]; then
  echo "DIR $directory"
  /bin/busybox ls -l "$directory"
 fi
 for file in nvram_net.txt nvram.txt; do
  path="$directory/$file"
  if [ -r "$path" ]; then
   echo "FILE $path"
   /bin/busybox head -c 8192 "$path"
   echo
  fi
 done
done
echo XOOM_WIFI_FILES_END
echo XOOM_ANDROID_DISPLAY_BEGIN
if [ -x /system/bin/dumpsys ]; then
 {
  /bin/busybox timeout -s KILL 2 /system/bin/dumpsys display
  echo "XOOM_DUMPSYS_DISPLAY_EXIT $?"
 } 2>&1 | /bin/busybox head -c 16384
 {
  /bin/busybox timeout -s KILL 2 /system/bin/dumpsys power
  echo "XOOM_DUMPSYS_POWER_EXIT $?"
 } 2>&1 | /bin/busybox head -c 8192
fi
echo XOOM_ANDROID_DISPLAY_END
echo XOOM_GFXINFO_BEGIN
if [ -x /system/bin/dumpsys ]; then
 for package in com.cyanogenmod.trebuchet com.google.android.setupwizard; do
  echo "XOOM_GFXINFO $package"
  /bin/busybox timeout -s KILL 2 /system/bin/dumpsys gfxinfo "$package" 2>&1 | /bin/busybox head -c 16384
  echo
 done
fi
echo XOOM_GFXINFO_END
echo XOOM_DISPLAY_END
