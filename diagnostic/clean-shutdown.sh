#!/bin/busybox sh
# Isolated shutdown profile only. All diagnostics stay on RAM or kernel console.
BB=/bin/busybox
OUT=/run/android44-shutdown.txt
note() { echo "XOOM_SHUTDOWN_$*" >> "$OUT"; echo "XOOM_SHUTDOWN_$*" > /dev/kmsg; }
stalled() {
 note "STALLED_$1 pid=$2"
 for file in status wchan stack; do
  [ ! -r "/proc/$2/$file" ] || $BB head -c 8192 "/proc/$2/$file" >> "$OUT" 2>/dev/null
 done
 # Root-only blocked-task diagnostic; never requests reboot/poweroff.
 [ ! -w /proc/sysrq-trigger ] || echo w > /proc/sysrq-trigger
}
stop() { note "BLOCKED_$1"; exit 1; }
run_checked() {
 label=$1; limit=$2; shift 2
 note "START_$label"
 "$@" > "/run/shutdown-$label.log" 2>&1 &
 worker=$!; elapsed=0
 while $BB kill -0 "$worker" 2>/dev/null; do
  if [ "$elapsed" -ge "$limit" ]; then
   stalled "$label" "$worker"
   $BB kill -KILL "$worker" 2>/dev/null
   # Do not wait for an uninterruptible child: SIGKILL cannot free a D-state wait.
   return 124
  fi
  $BB sleep 1
  elapsed=$((elapsed + 1))
 done
 wait "$worker"; result=$?
 $BB head -c 8192 "/run/shutdown-$label.log" >> "$OUT" 2>/dev/null
 note "END_$label rc=$result"
 return "$result"
}
identity() {
 target=$1; device=$2
 $BB awk -v t="$target" -v d="$device" '
 $5==t {n++; for(i=1;i<=NF;i++) if($i=="-")s=i;
  if($3!=d || $4!="/" || !s || $(s+1)!="ext4" || $(s+2)!="/dev/mmcblk0p" substr(d,5)) bad=1}
 END {exit n!=1 || bad}' /proc/self/mountinfo
}
case "$#:$1" in 1:shutdown|1:reboot) mode=$1;; *) exit 1;; esac
[ -f /bin/clean-shutdown-enabled ] || exit 1
[ "$($BB id -u)" = 0 ] || exit 1
$BB mkdir /run/xoom-shutdown.lock 2>/dev/null || exit 1
note "BEGIN_$mode"
identity /data 179:10 || stop data_identity
if $BB awk '$5=="/cache" && $3=="179:9" {found=1} END {exit !found}' /proc/self/mountinfo; then
 [ -f /bin/storage-cache-approved ] || stop cache_unapproved
 identity /cache 179:9 || stop cache_identity
 cache_persistent=1
else
 [ ! -f /bin/storage-cache-approved ] || stop cache_missing
 $BB awk '$5=="/cache" {n++;for(i=1;i<=NF;i++)if($i=="-")s=i;
  if($3!~/^0:/ || $4!="/" || !s || $(s+1)!="tmpfs")bad=1} END {exit n!=1 || bad}' /proc/self/mountinfo || stop cache_identity
 cache_persistent=0
fi
# Propagation changes do not flush or unmount the filesystem.
run_checked private_cache 10 $BB mount --make-private /cache || stop private_cache
run_checked private_data 10 $BB mount --make-private /data || stop private_data
run_checked initial_sync 30 $BB sync || stop initial_sync
# Android services, including sdcard, were stopped by init before this service.
targets=$($BB awk '$5 ~ /^\/storage\/emulated(\/[0-9]+)?$/ || $5 == "/mnt/shell/emulated" {print $5}' /proc/self/mountinfo | $BB sort -r)
for target in $targets; do
 run_checked emulated_unmount 10 $BB umount "$target" || stop emulated_unmount
done
# A clean RO remount is sufficient for poweroff and avoids kill_block_super /
# ext4_put_super / journal-thread destruction in the failing unmount-first path.
# No forced/lazy unmount and no fallback to a writable or unchecked filesystem.
if [ "$cache_persistent" = 1 ]; then
 run_checked cache_readonly 30 $BB mount -t ext4 -o remount,ro,nosuid,nodev,noatime /dev/mmcblk0p9 /cache || stop cache_readonly
fi
run_checked data_readonly 30 $BB mount -t ext4 -o remount,ro,nosuid,nodev,noatime /dev/mmcblk0p10 /data || stop data_readonly
# Require BOTH VFS and superblock RO for every eMMC alias in this namespace.
$BB awk '$3 ~ /^179:/ {s=0;for(i=1;i<=NF;i++)if($i=="-")s=i;
 if(!s || $6 !~ /(^|,)ro(,|$)/ || $6 ~ /(^|,)rw(,|$)/ ||
    $(s+3) !~ /(^|,)ro(,|$)/ || $(s+3) ~ /(^|,)rw(,|$)/)bad=1}
 END {exit bad}' /proc/self/mountinfo || stop writable_alias
identity /data 179:10 || stop final_data_identity
[ "$cache_persistent" != 1 ] || identity /cache 179:9 || stop final_cache_identity
run_checked final_sync 30 $BB sync || stop final_sync
volumes=/dev/mmcblk0p10
[ "$cache_persistent" != 1 ] || volumes="$volumes /dev/mmcblk0p9"
verify_volume() {
 volume=$1
 state=$($BB dd if="$volume" bs=1 skip=1082 count=2 2>/dev/null | $BB od -An -v -tx1 | $BB tr -d ' \n')
 incompat=$($BB dd if="$volume" bs=1 skip=1120 count=1 2>/dev/null | $BB od -An -v -tx1 | $BB tr -d ' \n')
 errors=$($BB dd if="$volume" bs=1 skip=1428 count=4 2>/dev/null | $BB od -An -v -tx1 | $BB tr -d ' \n')
 [ "$state" = 0100 ] && [ "${#incompat}" = 2 ] && [ "$errors" = 00000000 ] || return 1
 [ $((0x$incompat & 4)) = 0 ] || return 1
}
for volume in $volumes; do
 run_checked "superblock_${volume##*/}" 15 verify_volume "$volume" || stop filesystem_not_clean
done
note FILESYSTEM_CLEAN
# No more writes to p9/p10 after quiescing. Property service remains in PID1.
note "NATIVE_REQUEST_$mode"
run_checked native_handoff 10 /system/bin/setprop sys.xoom.shutdown_ready "$mode" || stop native_handoff
note "HANDOFF_$mode"
