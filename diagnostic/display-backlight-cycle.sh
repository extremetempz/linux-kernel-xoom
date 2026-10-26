#!/bin/busybox sh
# MANUAL test A only. Never invoked at boot, by a report, or by the build.
# No framebuffer/GPIO/suspend/charger operation. Restore on every normal exit.
[ "$#" -eq 1 ] && [ "$1" = --run-backlight-only ] || {
 echo 'Manual use only: display-backlight-cycle --run-backlight-only' >&2
 exit 2
}
p=/sys/class/backlight/lcd-backlight/brightness
saved=$(/bin/busybox cat "$p") || exit 1
case "$saved" in ''|*[!0-9]*) exit 1;; esac
[ "$saved" -gt 0 ] && [ "$saved" -le 255 ] || {
 echo 'Start with a visible display and brightness 1..255.' >&2
 exit 1
}
restore() { echo "$saved" > "$p"; }
trap restore EXIT
trap 'exit 1' HUP INT TERM
cycle=1
while [ "$cycle" -le 10 ]; do
 echo "BACKLIGHT_ONLY_CYCLE $cycle off"
 echo 0 > "$p" || exit 1
 /bin/busybox sleep 2
 echo "BACKLIGHT_ONLY_CYCLE $cycle restore=$saved"
 restore || exit 1
 /bin/busybox sleep 2
 cycle=$((cycle+1))
done
