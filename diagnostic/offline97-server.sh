#!/bin/busybox sh
# Reuse the existing nonce/hash framing, with only PING/REPORT; no shell/repair verbs.
/bin/busybox stty raw -echo -echonl -opost -onlcr <&0 || exit 1
while IFS= read -r -n 80 request; do
 case "$request" in
  PING\ *) verb=PING; nonce=${request#PING };;
  REPORT\ *) verb=REPORT; nonce=${request#REPORT };;
  *) continue;;
 esac
 [ "${#nonce}" = 32 ] || continue
 case "$nonce" in *[!0123456789abcdef]*) continue;; esac
 if [ "$verb" = PING ]; then /bin/busybox printf 'XOOM_READY_V2 %s\n' "$nonce"; continue; fi
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
