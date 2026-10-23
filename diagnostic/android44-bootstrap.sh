#!/bin/busybox sh
# Experimental image-30 integration; package only with prepare-android44.py.
# First Android boot: immutable eMMC policy, read-only system, RAM data only.
stage() { echo "XOOM_ANDROID44_STAGE $1" >> /run/android44-stages.txt; }
fail() {
 stage "FAILED_$1"
 while :; do /bin/busybox sleep 5; done
}
stage start
case "$(/bin/busybox uname -r)" in
 4.4.147-wingray-android44|4.4.147-wingray-android44-touch|4.4.147-wingray-android44-l2|4.4.147-wingray-android44-smp|4.4.147-wingray-android44-smp2|4.4.147-wingray-android44-smptrace) ;;
 *) fail release;;
esac
/bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx motorola,wingray || fail board
waited=0
while [ ! -d /sys/block/mmcblk0/mmcblk0p10 ] && [ "$waited" -lt 20 ]; do
 /bin/busybox sleep 1
 waited=$((waited + 1))
done
[ "$(/bin/busybox cat /sys/block/mmcblk0/size)" = 62521344 ] || fail disk_capacity
[ "$(/bin/busybox cat /sys/block/mmcblk0/ro)" = 1 ] || fail disk_readonly
while read number start size; do
 part="/sys/block/mmcblk0/mmcblk0p$number"
 [ "$(/bin/busybox cat "$part/start")" = "$start" ] || fail partition_start
 [ "$(/bin/busybox cat "$part/size")" = "$size" ] || fail partition_size
 [ "$(/bin/busybox cat "$part/ro")" = 1 ] || fail partition_readonly
done <<'XOOM_GEOMETRY'
1 51200 6144
2 57344 4096
3 61440 4096
4 65536 8192
5 73728 4096
6 77824 24576
7 102400 16384
8 118784 2097152
9 2215936 1048576
10 3264512 59247616
XOOM_GEOMETRY
stage readonly_geometry_passed
/bin/android44-abi-probe > /run/android44-abi.txt 2>&1
result=$?
echo "XOOM_ANDROID44_ABI_EXIT $result" >> /run/android44-abi.txt
[ "$result" -eq 0 ] || fail abi
stage abi_passed
if [ -x /bin/cpu-handoff-probe ]; then
 /bin/cpu-handoff-probe > /run/cpu-handoff.txt 2>&1
 result=$?
 echo "XOOM_CPU_HANDOFF_EXIT $result" >> /run/cpu-handoff.txt
 [ "$result" -eq 0 ] || fail cpu_handoff
 stage cpu_handoff_passed
fi
# Set the already-tested fixed framebuffer mode before any Android HAL opens it.
waited=0
while [ ! -e /dev/fb0 ] && [ "$waited" -lt 15 ]; do
 /bin/busybox sleep 1
 waited=$((waited + 1))
done
/bin/display-pattern > /run/display-pattern-result.txt 2>&1
result=$?
echo "XOOM_PATTERN_EXIT $result" >> /run/display-pattern-result.txt
[ "$result" -eq 0 ] || fail display
stage display_passed
/bin/busybox mkdir -p /system /data /cache /run/xoom-hw /run/xoom-egl /run/android-logs
/bin/busybox mount -t tmpfs -o size=256m,mode=0771,uid=1000,gid=1000,nosuid,nodev tmpfs /data || fail ram_data
/bin/busybox mount -t tmpfs -o size=96m,mode=0771,uid=1000,gid=2001,nosuid,nodev tmpfs /cache || fail ram_cache
# noload prevents ext4 journal replay, in addition to the kernel's RO policy.
/bin/busybox mount -t ext4 -o ro,noload,nosuid,nodev /dev/mmcblk0p8 /system || fail system_mount
/bin/busybox sha256sum -c /bin/android44-system-sha256 > /run/android44-system-check.txt 2>&1 || fail system_hashes
stage system_readonly_verified
# This ROM has no vendor HAL/EGL directories. Refuse an unreviewed layout.
[ ! -d /system/vendor/lib/hw ] && [ ! -d /system/vendor/lib/egl ] || fail vendor_layout
for name in gralloc.default audio.primary.default audio_policy.default power.default keystore.default local_time.default; do
 /bin/busybox cp "/system/lib/hw/$name.so" /run/xoom-hw/ || fail hal_copy
done
/bin/busybox cp /system/lib/egl/libGLES_android.so /run/xoom-egl/libGLES.so || fail egl_copy
/bin/busybox cp /system/lib/egl/libGLES_android.so /run/xoom-egl/libGLES_android.so || fail egl_copy
/bin/busybox mount -o bind /run/xoom-hw /system/lib/hw || fail hal_bind
/bin/busybox mount -o remount,bind,ro,nosuid,nodev /run/xoom-hw /system/lib/hw || fail hal_bind_ro
/bin/busybox mount -o bind /run/xoom-egl /system/lib/egl || fail egl_bind
/bin/busybox mount -o remount,bind,ro,nosuid,nodev /run/xoom-egl /system/lib/egl || fail egl_bind_ro
stage ram_graphics_overlays_ready
# Android init must be PID1 to create its property workspace and reap services.
stage exec_original_android_init
exec /init.android
fail android_init_exec
