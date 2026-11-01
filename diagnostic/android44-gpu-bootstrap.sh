#!/bin/busybox sh
# Experimental combined NVIDIA Android integration; package only with prepare-android44.py.
# First Android boot: immutable eMMC policy, read-only system, RAM data only.
stage() { echo "XOOM_ANDROID44_STAGE $1" >> /run/android44-stages.txt; }
fail() {
 stage "FAILED_$1"
 while :; do /bin/busybox sleep 5; done
}
stage start
case "$(/bin/busybox uname -r)" in
 4.4.147-wingray-android44-gpu) ;;
 *) fail release;;
esac
/bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx motorola,wingray || fail board
persistent=0
if [ -e /sys/firmware/devicetree/base/sdhci@c8000600/motorola,xoom-persistent-storage ]; then
 persistent=1
elif [ -e /sys/firmware/devicetree/base/sdhci@c8000600/motorola,xoom-firstboot-ro ]; then
 persistent=0
else
 fail storage_profile_marker_missing
fi
inspect=0
[ -e /sys/firmware/devicetree/base/motorola,wingray-storage-inspect ] && inspect=1
write_test=0
[ -e /sys/firmware/devicetree/base/motorola,wingray-storage-write-test ] && write_test=1
stage "storage_mode_persistent_${persistent}_inspect_${inspect}_write_${write_test}"
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
mount_system_readonly() {
 # noload prevents ext4 journal replay, in addition to the kernel's RO policy.
 /bin/busybox mount -t ext4 -o ro,noload,nosuid,nodev /dev/mmcblk0p8 /system || fail system_mount
 /bin/busybox sha256sum -c /bin/android44-system-sha256 > /run/android44-system-check.txt 2>&1 || fail system_hashes
 stage system_readonly_verified
}
if [ "$persistent" = 1 ]; then
 mount_system_readonly
 if [ "$inspect" = 1 ]; then
  /bin/android44-storage-inspect > /run/storage-inspect-console.txt 2>&1
  echo "XOOM_STORAGE_INSPECT_RC $?" >> /run/android44-storage-inspect.txt
  stage inspection_complete_read_only
  while :; do /bin/busybox sleep 5; done
 fi
 # Fail closed before releasing either partition. No format, journal replay or
 # repair is allowed here; Stage A must inspect the filesystem first.
 data_size=$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p10/size)
 cache_size=$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p9/size)
 data_tail_skip=$((data_size - 32))
 cache_tail_skip=$((cache_size - 32))
 /bin/busybox dd if=/dev/mmcblk0p10 of=/run/storage-p10-tail.bin bs=512 skip="$data_tail_skip" count=32 2>/dev/null || fail data_tail_read
 /bin/busybox dd if=/dev/mmcblk0p9 of=/run/storage-p9-tail.bin bs=512 skip="$cache_tail_skip" count=32 2>/dev/null || fail cache_tail_read
 data_footer=$(/bin/busybox od -An -v -tx1 /run/storage-p10-tail.bin | /bin/busybox tr -d ' \n')
 cache_footer=$(/bin/busybox od -An -v -tx1 /run/storage-p9-tail.bin | /bin/busybox tr -d ' \n')
 case "$data_footer" in *c4b1b5d0*) fail encrypted_userdata;; esac
 case "$cache_footer" in *c4b1b5d0*) fail encrypted_cache;; esac
 data_magic=$(/bin/busybox dd if=/dev/mmcblk0p10 bs=1 skip=1080 count=2 2>/dev/null | /bin/busybox od -An -v -tx1 | /bin/busybox tr -d ' \n')
 cache_magic=$(/bin/busybox dd if=/dev/mmcblk0p9 bs=1 skip=1080 count=2 2>/dev/null | /bin/busybox od -An -v -tx1 | /bin/busybox tr -d ' \n')
 [ "$data_magic" = 53ef ] || fail data_not_ext4
 [ "$cache_magic" = 53ef ] || fail cache_not_ext4
 stage persistent_fs_identity_checked
 /bin/storage-policy > /run/android44-storage-policy.txt 2>&1 || fail storage_policy
 [ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p9/ro)" = 0 ] || fail cache_policy
 [ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p10/ro)" = 0 ] || fail data_policy
 [ "$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p8/ro)" = 1 ] || fail system_policy
 [ "$(/bin/busybox cat /sys/block/mmcblk0/ro)" = 1 ] || fail disk_policy
 /bin/busybox grep -q ' /data ' /proc/mounts && fail data_already_mounted
 /bin/busybox grep -q ' /cache ' /proc/mounts && fail cache_already_mounted
 if [ "$write_test" = 1 ]; then
  /bin/busybox mount -t ext4 -o rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic /dev/mmcblk0p10 /data || fail write_test_data_mount
  /bin/storage-write-test > /run/storage-write-console.txt 2>&1
  echo "XOOM_STORAGE_WRITE_TEST_RC $?" >> /run/android44-storage-write-test.txt
  stage persistent_write_test_complete
  while :; do /bin/busybox sleep 5; done
 fi
 /bin/busybox grep -q ' /data ' /proc/mounts && fail data_already_mounted
 /bin/busybox grep -q ' /cache ' /proc/mounts && fail cache_already_mounted
 # Original ROM options, without noload: writable ext4 may replay its journal.
 /bin/busybox mount -t ext4 -o rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic /dev/mmcblk0p10 /data || fail persistent_data_mount
 /bin/busybox mount -t ext4 -o rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic /dev/mmcblk0p9 /cache || fail persistent_cache_mount
 stage persistent_data_cache_mounted
else
 /bin/busybox mount -t tmpfs -o size=256m,mode=0771,uid=1000,gid=1000,nosuid,nodev tmpfs /data || fail ram_data
 /bin/busybox mount -t tmpfs -o size=96m,mode=0771,uid=1000,gid=2001,nosuid,nodev tmpfs /cache || fail ram_cache
 mount_system_readonly
fi
# This ROM has no vendor HAL/EGL directories. Refuse an unreviewed layout.
[ ! -d /system/vendor/lib/hw ] && [ ! -d /system/vendor/lib/egl ] || fail vendor_layout
for name in gralloc.tegra hwcomposer.tegra audio.primary.default audio_policy.default power.default keystore.default local_time.default; do
 /bin/busybox cp "/system/lib/hw/$name.so" /run/xoom-hw/ || fail hal_copy
done
# The opt-in display profile has a backlight-class KitKat HAL. Do not copy
# the old lights HAL: it uses LED-class paths and unrelated charger GPIOs.
if [ -r /sys/firmware/devicetree/base/motorola,wingray-display-pm-test ]; then
 /bin/busybox cp /bin/lights.stingray.so /run/xoom-hw/lights.stingray.so || fail lights_hal_copy
fi
# Only the separate Bluetooth profile exposes the original Android HAL.
# Keep firmware/vendor library on the existing read-only system partition.
if [ -r /sys/firmware/devicetree/base/bluetooth-power/compatible ]; then
 /bin/busybox cp /system/lib/hw/bluetooth.default.so /run/xoom-hw/ || fail bluetooth_hal_copy
fi
for name in libEGL_tegra libGLESv1_CM_tegra libGLESv2_tegra; do
 /bin/busybox cp "/system/lib/egl/$name.so" /run/xoom-egl/ || fail egl_copy
done
# Match the already successful vendor loader default; no software EGL fallback.
/bin/busybox printf '0 1 tegra\n' > /run/xoom-egl/egl.cfg
/bin/busybox mount -o bind /run/xoom-hw /system/lib/hw || fail hal_bind
/bin/busybox mount -o remount,bind,ro,nosuid,nodev /run/xoom-hw /system/lib/hw || fail hal_bind_ro
/bin/busybox mount -o bind /run/xoom-egl /system/lib/egl || fail egl_bind
/bin/busybox mount -o remount,bind,ro,nosuid,nodev /run/xoom-egl /system/lib/egl || fail egl_bind_ro
stage ram_graphics_overlays_ready
# healthd discovers supply paths once, at startup. Opt-in monitor must
# enumerate before Android init; failure leaves the diagnostic USB available.
if [ -r /sys/firmware/devicetree/base/wingray_battery_monitor/compatible ]; then
 waited=0
 while ! /bin/busybox cat /sys/class/power_supply/battery/capacity >/dev/null 2>&1 || ! /bin/busybox cat /sys/class/power_supply/ac/online >/dev/null 2>&1; do
  [ "$waited" -lt 30 ] || break
  /bin/busybox sleep 1
  waited=$((waited + 1))
 done
 if /bin/busybox cat /sys/class/power_supply/battery/capacity >/dev/null 2>&1 && /bin/busybox cat /sys/class/power_supply/ac/online >/dev/null 2>&1; then
  stage battery_monitor_enumerated
 else
  echo WARN_battery_monitor_missing >&2
 fi
fi
# Android init must be PID1 to create its property workspace and reap services.
stage exec_original_android_init
exec /init.android
fail android_init_exec
