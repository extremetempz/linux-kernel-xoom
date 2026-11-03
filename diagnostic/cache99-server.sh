#!/bin/busybox sh
# Reuse the existing nonce/hash framing, with only PING/REPORT; no shell/repair verbs.
/bin/busybox rm -f /run/cache99-preflight-nonce
/bin/busybox stty raw -echo -echonl -opost -onlcr <&0 || exit 1
while IFS= read -r -n 80 request; do
 case "$request" in
  PING\ *) verb=PING; nonce=${request#PING };;
  REPORT\ *) verb=REPORT; nonce=${request#REPORT };;
  PREFLIGHT_P9\ *) verb=PREFLIGHT; nonce=${request#PREFLIGHT_P9 };;
  REPAIR_P9\ *) verb=REPAIR; nonce=${request#REPAIR_P9 };;
  *) continue;;
 esac
 [ "${#nonce}" = 32 ] || continue
 case "$nonce" in *[!0123456789abcdef]*) continue;; esac
 if [ "$verb" = PING ]; then /bin/busybox printf 'XOOM_READY_V2 %s\n' "$nonce"; continue; fi
 if [ "$verb" = PREFLIGHT ]; then
  /bin/busybox sh /bin/cache99-preflight > /run/cache99-preflight.txt 2>&1
  rc=$?
  /bin/busybox cat /run/cache99-preflight.txt
  if [ "$rc" = 0 ]; then echo "$nonce" > /run/cache99-preflight-nonce; else /bin/busybox rm -f /run/cache99-preflight-nonce; fi
  continue
 fi
 if [ "$verb" = REPAIR ]; then
  [ ! -e /run/cache99-attempted ] || continue
  [ "$(/bin/busybox cat /run/cache99-preflight-nonce 2>/dev/null)" = "$nonce" ] || continue
  /bin/busybox printf 'CACHE99_ARMED %s\n' "$nonce"
  # Bounded confirmation wait. A disconnect/new session must preflight again.
  if ! IFS= read -r -t 60 -n 80 confirm || [ "$confirm" != "REPAIR_P9_CONFIRM $nonce" ]; then
   /bin/busybox rm -f /run/cache99-preflight-nonce
   echo CACHE99_NOT_CONFIRMED
   continue
  fi
  /bin/busybox rm -f /run/cache99-preflight-nonce
  /bin/busybox sh /bin/cache99-repair
  continue
 fi
 /bin/busybox sh /bin/diagnostic-report "$nonce" > /run/diagnostic-report.txt 2>&1
 rc=$?
 [ "$rc" = 0 ] || continue
 size=$(/bin/busybox wc -c < /run/diagnostic-report.txt);size=$((size+0))
 [ "$size" -gt 0 ] && [ "$size" -le 524288 ] || continue
 checksum=$(/bin/busybox sha256sum /run/diagnostic-report.txt) || continue
 checksum=${checksum%% *}
 /bin/busybox base64 /run/diagnostic-report.txt > /run/diagnostic-report.b64 || continue
 /bin/busybox printf 'XOOM_REPORT_V2 %s %s %s\n' "$nonce" "$size" "$checksum"
 /bin/busybox cat /run/diagnostic-report.b64
 /bin/busybox printf '\nXOOM_END_V2 %s\n' "$nonce"
done
