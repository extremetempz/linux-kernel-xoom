#!/bin/busybox sh
# One fixed read-only request. USB input is never evaluated as shell code.
/bin/busybox stty raw -echo -echonl -opost -onlcr <&0 || exit 1
while IFS= read -r -n 80 request; do
 case "$request" in
  REPORT\ *) verb=REPORT; nonce=${request#REPORT } ;;
  PING\ *) verb=PING; nonce=${request#PING } ;;
  *) continue ;;
 esac
 [ "${#nonce}" -eq 32 ] || continue
 case "$nonce" in *[!0123456789abcdef]*) continue ;; esac
 if [ "$verb" = PING ]; then
  /bin/busybox printf 'XOOM_READY_V2 %s\n' "$nonce"
  continue
 fi
 /bin/busybox sh /bin/diagnostic-report "$nonce" > /run/diagnostic-report.txt 2>&1
 rc=$?
 if [ "$rc" -ne 0 ]; then
  /bin/busybox printf 'XOOM_ERROR_V2 %s REPORT_FAILED\n' "$nonce"
  continue
 fi
 size=$(/bin/busybox wc -c < /run/diagnostic-report.txt)
 size=$((size + 0))
 if [ "$size" -le 0 ] || [ "$size" -gt 524288 ]; then
  /bin/busybox printf 'XOOM_ERROR_V2 %s REPORT_SIZE\n' "$nonce"
  continue
 fi
 checksum=$(/bin/busybox sha256sum /run/diagnostic-report.txt) || continue
 checksum=${checksum%% *}
 # Prepare encoding before publishing a header. No prompts/command echo.
 /bin/busybox base64 /run/diagnostic-report.txt > /run/diagnostic-report.b64 || continue
 /bin/busybox printf 'XOOM_REPORT_V2 %s %s %s\n' "$nonce" "$size" "$checksum"
 /bin/busybox cat /run/diagnostic-report.b64
 /bin/busybox printf '\nXOOM_END_V2 %s\n' "$nonce"
done
