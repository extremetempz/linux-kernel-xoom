#!/bin/busybox sh
# Bounded root-only framebuffer blank test. No shell input is evaluated.
# Writes only fb0/blank, always attempts unblank restoration, then exits.
FB=/sys/class/graphics/fb0/blank
STATE=/sys/class/graphics/fb0/state
ARM=/sys/class/graphics/fb0/wingray_dc_test
dc_test=0
if [ "$#" -ne 0 ]; then
 [ "$#" -eq 1 ] && [ "$1" = --dc ] || exit 1
 [ "$(/bin/busybox id -u)" = 0 ] && [ -e "$ARM" ] || exit 1
 [ "$(/bin/busybox cat "$ARM")" = 0 ] || exit 1
 dc_test=1
fi
restore()
{
 /bin/busybox sh -c "echo 0 > $FB" >/dev/null 2>&1
 [ "$dc_test" -eq 0 ] || { echo 0 > "$ARM"; } >/dev/null 2>&1
}
trap restore EXIT HUP INT TERM
echo XOOM_FB_BLANK_TEST_V1
echo "FB_BLANK_UID $(/bin/busybox id -u 2>&1)"
if [ "$dc_test" -eq 1 ]; then
 echo 1 > "$ARM" || exit 1
 [ "$(/bin/busybox cat "$ARM")" = 1 ] || exit 1
 echo DCTEST_ARMED_1
fi
echo "FB_BLANK_STATE_BEFORE $(/bin/busybox cat "$STATE" 2>&1)"
echo "FB_BLANK_WRITE4_BEGIN"
/bin/busybox sh -c "echo 4 > $FB" 2>&1
echo "FB_BLANK_WRITE4_RC $?"
/bin/busybox sleep 1
echo "FB_BLANK_STATE_OFF $(/bin/busybox cat "$STATE" 2>&1)"
echo FB_BLANK_DMESG_OFF_BEGIN
/bin/busybox dmesg 2>&1 | /bin/busybox grep -E 'WG_DC85|Wingray (display|backlight|DC test|native mode)|tegra_fb|fb_blank|tegradc' | /bin/busybox tail -100
echo FB_BLANK_DMESG_OFF_END
echo "FB_BLANK_WRITE0_BEGIN"
/bin/busybox sh -c "echo 0 > $FB" 2>&1
echo "FB_BLANK_WRITE0_RC $?"
/bin/busybox sleep 1
echo "FB_BLANK_STATE_ON $(/bin/busybox cat "$STATE" 2>&1)"
echo FB_BLANK_DMESG_ON_BEGIN
/bin/busybox dmesg 2>&1 | /bin/busybox grep -E 'WG_DC85|Wingray (display|backlight|DC test|native mode)|tegra_fb|fb_blank|tegradc' | /bin/busybox tail -100
echo FB_BLANK_DMESG_ON_END
if [ "$dc_test" -eq 1 ]; then
 echo 0 > "$ARM" 2>&1
 echo "DCTEST_DISARM_RC $?"
 echo "DCTEST_ARMED_AFTER $(/bin/busybox cat "$ARM" 2>&1)"
fi
echo XOOM_FB_BLANK_TEST_END
