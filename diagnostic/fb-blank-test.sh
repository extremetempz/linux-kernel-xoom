#!/bin/busybox sh
# Bounded root-only framebuffer blank test. No shell input is evaluated.
# Writes only fb0/blank, always attempts unblank restoration, then exits.
FB=/sys/class/graphics/fb0/blank
STATE=/sys/class/graphics/fb0/state
restore()
{
 /bin/busybox sh -c "echo 0 > $FB" >/dev/null 2>&1
}
trap restore EXIT HUP INT TERM
echo XOOM_FB_BLANK_TEST_V1
echo "FB_BLANK_UID $(/bin/busybox id -u 2>&1)"
echo "FB_BLANK_STATE_BEFORE $(/bin/busybox cat "$STATE" 2>&1)"
echo "FB_BLANK_WRITE4_BEGIN"
/bin/busybox sh -c "echo 4 > $FB" 2>&1
echo "FB_BLANK_WRITE4_RC $?"
/bin/busybox sleep 1
echo "FB_BLANK_STATE_OFF $(/bin/busybox cat "$STATE" 2>&1)"
echo FB_BLANK_DMESG_OFF_BEGIN
/bin/busybox dmesg 2>&1 | /bin/busybox grep -E 'Wingray (display|backlight)|tegra_fb|fb_blank|tegradc' | /bin/busybox tail -40
echo FB_BLANK_DMESG_OFF_END
echo "FB_BLANK_WRITE0_BEGIN"
/bin/busybox sh -c "echo 0 > $FB" 2>&1
echo "FB_BLANK_WRITE0_RC $?"
/bin/busybox sleep 1
echo "FB_BLANK_STATE_ON $(/bin/busybox cat "$STATE" 2>&1)"
echo FB_BLANK_DMESG_ON_BEGIN
/bin/busybox dmesg 2>&1 | /bin/busybox grep -E 'Wingray (display|backlight)|tegra_fb|fb_blank|tegradc' | /bin/busybox tail -40
echo FB_BLANK_DMESG_ON_END
echo XOOM_FB_BLANK_TEST_END
