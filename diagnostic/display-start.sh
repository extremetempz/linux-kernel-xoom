#!/bin/busybox sh
# Runs once in parallel with USB service. Never block diagnostic access on DRM.
if [ "$(/bin/busybox uname -r)" != '4.4.147-wingray-display' ]; then
 echo XOOM_PATTERN_DENIED_RELEASE
 exit 0
fi
if ! /bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx motorola,wingray; then
 echo XOOM_PATTERN_DENIED_BOARD
 exit 0
fi
waited=0
while [ "$waited" -lt 15 ] && [ ! -c /dev/fb0 ]; do
 /bin/busybox sleep 1
 waited=$((waited + 1))
done
echo "XOOM_PATTERN_WAIT_SECONDS $waited"
if [ ! -c /dev/fb0 ]; then
 echo XOOM_PATTERN_NO_FB0
 exit 0
fi
/bin/display-pattern
echo "XOOM_PATTERN_EXIT $?"
