#!/bin/busybox sh
# Diagnostic only: capture p9/cache holders at power-off, never power off.
exec </dev/ttyGS0 >/dev/ttyGS0 2>&1
BB=/bin/busybox
OUT=/cache/xoom-cache-holders
: > "$OUT" 2>/dev/null
say() { echo "$@"; echo "$@" >> "$OUT"; }
say XOOM_CACHE_HOLDERS_BEGIN
say "DATE $($BB date -u +%Y-%m-%dT%H:%M:%SZ)"
say "MOUNTS"
$BB cat /proc/mounts | $BB grep -E ' /cache | /data |mmcblk0p9|mmcblk0p10' >> "$OUT"
say "MOUNTINFO"
$BB cat /proc/self/mountinfo | $BB grep -E ' /cache | /data |mmcblk0p9|mmcblk0p10' >> "$OUT"
say "FDS"
for proc in /proc/[0-9]*; do
 pid=${proc#/proc/}
 for fd in "$proc"/fd/*; do
  [ -e "$fd" ] || continue
  target=$($BB readlink "$fd" 2>/dev/null) || continue
  case "$target" in
   /cache|/cache/*|/dev/mmcblk0p9*)
    comm=$($BB cat "$proc/comm" 2>/dev/null)
    say "HOLDER pid=$pid comm=$comm fd=${fd##*/} target=$target"
    ;;
  esac
 done
done
say "FUSER"
$BB fuser -m /cache >> "$OUT" 2>&1 || true
say "SYNC"
$BB sync
say "FDS_AFTER_SYNC"
for proc in /proc/[0-9]*; do
 pid=${proc#/proc/}
 for fd in "$proc"/fd/*; do
  [ -e "$fd" ] || continue
  target=$($BB readlink "$fd" 2>/dev/null) || continue
  case "$target" in
   /cache|/cache/*|/dev/mmcblk0p9*)
    comm=$($BB cat "$proc/comm" 2>/dev/null)
    say "HOLDER_AFTER_SYNC pid=$pid comm=$comm fd=${fd##*/} target=$target"
    ;;
  esac
 done
done
say XOOM_CACHE_HOLDERS_END
while :; do $BB sleep 5; done
