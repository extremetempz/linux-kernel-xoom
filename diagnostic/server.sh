#!/bin/busybox sh
# Fixed requests: read-only PING/REPORT plus bounded FBTEST. USB input is never evaluated as shell code.
/bin/busybox stty raw -echo -echonl -opost -onlcr <&0 || exit 1
while IFS= read -r -n 80 request; do
 case "$request" in
  REPORT\ *) verb=REPORT; nonce=${request#REPORT } ;;
  FBTEST\ *) verb=FBTEST; nonce=${request#FBTEST } ;;
  PING\ *) verb=PING; nonce=${request#PING } ;;
  *) continue ;;
 esac
 [ "${#nonce}" -eq 32 ] || continue
 case "$nonce" in *[!0123456789abcdef]*) continue ;; esac
 if [ "$verb" = PING ]; then
  /bin/busybox printf 'XOOM_READY_V2 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = FBTEST ]; then
  if [ ! -x /bin/fb-blank-test ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s FBTEST_MISSING\n' "$nonce"
   continue
  fi
  /bin/busybox sh /bin/fb-blank-test > /run/fb-blank-test.txt 2>&1
  rc=$?
  size=$(/bin/busybox wc -c < /run/fb-blank-test.txt)
  size=$((size + 0))
  if [ "$rc" -ne 0 ] || [ "$size" -le 0 ] || [ "$size" -gt 524288 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s FBTEST_FAILED\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/fb-blank-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/fb-blank-test.txt > /run/fb-blank-test.b64 || continue
  /bin/busybox printf 'XOOM_FBTEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/fb-blank-test.b64
  /bin/busybox printf '\nXOOM_FBTEST_END_V1 %s\n' "$nonce"
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
