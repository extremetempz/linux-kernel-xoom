#!/bin/busybox sh
# Read-only, fixed-scope Android44 evidence. Never mounts, changes properties,
# opens block devices, or interprets USB input. Output is private diagnostic data.
# BusyBox 1.31.0 timeout supports [-s SIG] SECS PROG ARGS (tagged upstream
# coreutils/timeout.c); the target applet itself still needs hardware validation.

echo XOOM_ANDROID44_POLICY_BEGIN_V1
release=$(/bin/busybox uname -r)
echo "XOOM_ANDROID44_RELEASE $release"
case "$release" in
 4.4.147-wingray-android44|4.4.147-wingray-android44-touch|4.4.147-wingray-android44-l2|4.4.147-wingray-android44-smp|4.4.147-wingray-android44-smp2|4.4.147-wingray-android44-smptrace|4.4.147-wingray-android44-gpu) ;;
 *)
 echo XOOM_ANDROID44_DENIED_RELEASE
 echo XOOM_ANDROID44_POLICY_END_V1
 exit 0;;
esac
if ! /bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx motorola,wingray; then
 echo XOOM_ANDROID44_DENIED_BOARD
 echo XOOM_ANDROID44_POLICY_END_V1
 exit 0
fi
echo 'XOOM_ANDROID44_BOARD motorola,wingray'
for name in mmcblk0 mmcblk0p1 mmcblk0p2 mmcblk0p3 mmcblk0p4 mmcblk0p5 mmcblk0p6 mmcblk0p7 mmcblk0p8 mmcblk0p9 mmcblk0p10; do
 path="/sys/block/mmcblk0/$name/ro"
 [ "$name" != mmcblk0 ] || path=/sys/block/mmcblk0/ro
 value=missing
 if [ -r "$path" ]; then value=$(/bin/busybox head -c 16 "$path"); fi
 case "$value" in 0|1) ;; *) value=missing;; esac
 echo "XOOM_ANDROID44_BLOCK_RO $name $value"
done
echo XOOM_ANDROID44_MOUNTINFO_BEGIN
/bin/busybox head -c 16384 /proc/self/mountinfo
echo
echo XOOM_ANDROID44_MOUNTINFO_END
# Only accept the sdcard process's exact fixed RAM-data command line. There is
# no assumption that an arbitrary FUSE mount uses /data/media.
sdcard=unverified
count=0
for process in /proc/[0-9]*; do
 [ "$count" -lt 512 ] || break
 count=$((count + 1))
 [ -r "$process/comm" ] || continue
 IFS= read -r process_name < "$process/comm" || continue
 [ "$process_name" = sdcard ] || continue
 [ -r "$process/cmdline" ] || continue
 command=$(/bin/busybox head -c 256 "$process/cmdline" | /bin/busybox tr '\000' '\n')
 if [ "$command" = '/system/bin/sdcard
/data/media
/mnt/shell/emulated
1023
1023' ]; then
  sdcard=verified
  break
 fi
done
echo "XOOM_ANDROID44_SDCARD_RAM_SOURCE $sdcard"
echo XOOM_ANDROID44_POLICY_END_V1

echo XOOM_ANDROID44_INPUT_BEGIN
if [ -d /dev/input ]; then
 echo XOOM_ANDROID44_INPUT_DIRECTORY present
 /bin/busybox ls -ld /dev/input
else
 echo XOOM_ANDROID44_INPUT_DIRECTORY missing
fi
echo XOOM_ANDROID44_INPUT_END

# Files must be regular files, not final-component symlinks. All paths below
# are fixed, and file contents are capped even if a failing service floods RAM.
bounded_file() {
 path=$1
 limit=$2
 if [ -f "$path" ] && [ ! -L "$path" ]; then
  /bin/busybox head -c "$limit" "$path"
  echo
 else
  echo XOOM_ANDROID44_FILE_UNAVAILABLE
 fi
}
echo XOOM_ANDROID44_STAGES_BEGIN
bounded_file /run/android44-stages.txt 4096
echo XOOM_ANDROID44_STAGES_END
echo XOOM_ANDROID44_ABI_BEGIN
bounded_file /run/android44-abi.txt 8192
echo XOOM_ANDROID44_ABI_END
echo XOOM_ANDROID44_SYSTEM_CHECK_BEGIN
bounded_file /run/android44-system-check.txt 4096
echo XOOM_ANDROID44_SYSTEM_CHECK_END
echo XOOM_ANDROID44_POWERCTL_BEGIN
bounded_file /run/android44-powerctl.txt 4096
echo XOOM_ANDROID44_POWERCTL_END
echo XOOM_ANDROID44_MEMINFO_BEGIN
/bin/busybox head -c 8192 /proc/meminfo
echo
echo XOOM_ANDROID44_MEMINFO_END
echo XOOM_ANDROID44_PROCESSES_BEGIN
/bin/busybox ps | /bin/busybox head -c 8192
echo
echo XOOM_ANDROID44_PROCESSES_END
echo XOOM_ANDROID44_SERVICE_LOGS_BEGIN
for service in healthd servicemanager vold netd debuggerd surfaceflinger zygote drm media keystore installd sdcard; do
 echo "XOOM_ANDROID44_SERVICE_LOG $service"
 bounded_file "/run/android-logs/$service/stdout.txt" 4096
done
echo XOOM_ANDROID44_SERVICE_LOGS_END

# Inspect native Android tools only after the fixed system mount is RO and
# journal recovery is disabled. Check the live table, never a bootstrap claim.
if /bin/busybox awk '
 $2 == "/system" {
  count++
  valid=($1 == "/dev/mmcblk0p8" || $1 == "/dev/block/mmcblk0p8") && $3 == "ext4"
  n=split($4,opts,","); ro=0; recovery=0; rw=0
  for (i=1;i<=n;i++) { if(opts[i]=="ro")ro=1; if(opts[i]=="rw")rw=1; if(opts[i]=="noload"||opts[i]=="norecovery")recovery=1 }
 }
 END { exit !(count==1 && valid && ro && !rw && recovery) }
' /proc/mounts; then
 echo XOOM_ANDROID44_PROPERTIES_BEGIN
 if [ -x /system/bin/getprop ]; then
  {
   /bin/busybox timeout -s KILL 2 /system/bin/getprop
   echo "XOOM_ANDROID44_GETPROP_EXIT $?"
  } 2>&1 | /bin/busybox grep -E '^\[(sys\.boot_completed|dev\.bootcomplete|ro\.hardware|ro\.build\.version\.release|ro\.kernel\.qemu|ro\.kernel\.qemu\.gles|init\.svc\.(healthd|servicemanager|vold|netd|debuggerd|surfaceflinger|zygote|drm|media|keystore|installd|sdcard))\]:|^XOOM_ANDROID44_GETPROP_EXIT ' | /bin/busybox head -c 8192
 else
  echo XOOM_ANDROID44_GETPROP_UNAVAILABLE
 fi
 echo
 echo XOOM_ANDROID44_PROPERTIES_END
 echo XOOM_ANDROID44_LOGCAT_BEGIN
 if [ -x /system/bin/logcat ]; then
  {
   /bin/busybox timeout -s KILL 2 /system/bin/logcat -d -t 200
   echo "XOOM_ANDROID44_LOGCAT_EXIT $?"
  } 2>&1 | /bin/busybox head -c 32768
 else
  echo XOOM_ANDROID44_LOGCAT_UNAVAILABLE
 fi
 echo
 echo XOOM_ANDROID44_LOGCAT_END
 echo XOOM_ANDROID44_GPU_COMPOSITOR_BEGIN
 if [ -x /system/bin/dumpsys ]; then
  {
   /bin/busybox timeout -s KILL 3 /system/bin/dumpsys SurfaceFlinger
   echo "XOOM_ANDROID44_GPU_DUMPSYS_EXIT $?"
  } 2>&1 | /bin/busybox head -c 65536
 fi
 echo XOOM_ANDROID44_GPU_COMPOSITOR_END
 echo XOOM_ANDROID44_GPU_NODES_BEGIN
 /bin/busybox ls -l /dev/nvhost-ctrl /dev/nvhost-gr2d /dev/nvhost-gr3d /dev/nvmap /dev/graphics/fb0
 echo XOOM_ANDROID44_GPU_NODES_END
 [ ! -x /bin/bluetooth-report ] || /bin/bluetooth-report
else
 echo XOOM_ANDROID44_NATIVE_READS_DENIED_MOUNT
fi

# Tombstones are read only if /data is presently tmpfs; never inspect preserved
# userdata. Fixed ten file names also bound directory traversal and output.
if /bin/busybox awk '$2=="/data" {count++; valid=($3=="tmpfs")} END {exit !(count==1 && valid)}' /proc/mounts; then
 echo XOOM_ANDROID44_TOMBSTONES_BEGIN
 for number in 00 01 02 03 04 05 06 07 08 09; do
  echo "XOOM_ANDROID44_TOMBSTONE $number"
  bounded_file "/data/tombstones/tombstone_$number" 4096
 done
 echo XOOM_ANDROID44_TOMBSTONES_END
else
 echo XOOM_ANDROID44_TOMBSTONES_DENIED_DATA
fi
[ ! -x /bin/battery-report ] || /bin/battery-report
[ ! -x /bin/power-report ] || /bin/power-report
echo XOOM_ANDROID44_REPORT_DONE_V1
