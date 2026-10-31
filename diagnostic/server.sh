#!/bin/busybox sh
# Fixed requests: read-only PING/REPORT plus bounded FBTEST. USB input is never evaluated as shell code.
/bin/busybox stty raw -echo -echonl -opost -onlcr <&0 || exit 1
while IFS= read -r -n 80 request; do
 case "$request" in
  REPORT\ *) verb=REPORT; nonce=${request#REPORT } ;;
  FBTEST\ *) verb=FBTEST; nonce=${request#FBTEST } ;;
  DCTEST\ *) verb=DCTEST; nonce=${request#DCTEST } ;;
  DEVICEPMTEST\ *) verb=DEVICEPMTEST; nonce=${request#DEVICEPMTEST } ;;
  DPMTEST\ *) verb=DPMTEST; nonce=${request#DPMTEST } ;;
  DPMSTATUS\ *) verb=DPMSTATUS; nonce=${request#DPMSTATUS } ;;
  BOOTID\ *) verb=BOOTID; nonce=${request#BOOTID } ;;
  CPU1TEST\ *) verb=CPU1TEST; nonce=${request#CPU1TEST } ;;
  LATETEST\ *) verb=LATETEST; nonce=${request#LATETEST } ;;
  SYSCTEST\ *) verb=SYSCTEST; nonce=${request#SYSCTEST } ;;
  LATESTATUS\ *) verb=LATESTATUS; nonce=${request#LATESTATUS } ;;
  SYSSTATUS\ *) verb=SYSSTATUS; nonce=${request#SYSSTATUS } ;;
  LP2TEST\ *) verb=LP2TEST; nonce=${request#LP2TEST } ;;
  LP2STATUS\ *) verb=LP2STATUS; nonce=${request#LP2STATUS } ;;
  FREEZERTEST\ *) verb=FREEZERTEST; nonce=${request#FREEZERTEST } ;;
  WAKETEST\ *) verb=WAKETEST; nonce=${request#WAKETEST } ;;
  PSTORE\ *) verb=PSTORE; nonce=${request#PSTORE } ;;
  PING\ *) verb=PING; nonce=${request#PING } ;;
  *) continue ;;
 esac
 [ "${#nonce}" -eq 32 ] || continue
 case "$nonce" in *[!0123456789abcdef]*) continue ;; esac
 if [ "$verb" = PING ]; then
  /bin/busybox printf 'XOOM_READY_V2 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = BOOTID ]; then
  /bin/busybox printf 'XOOM_BOOTID_V1 %s %s\n' "$nonce" "$(/bin/busybox cat /proc/sys/kernel/random/boot_id)"
  continue
 fi
 if [ "$verb" = PSTORE ]; then
  if [ ! -x /bin/pstore-report ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s PSTORE_MISSING\n' "$nonce"
   continue
  fi
  /bin/busybox sh /bin/pstore-report > /run/pstore-report.txt 2>&1
  rc=$?
  size=$(/bin/busybox wc -c < /run/pstore-report.txt)
  size=$((size + 0))
  if [ "$rc" -ne 0 ] || [ "$size" -le 0 ] || [ "$size" -gt 2097152 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s PSTORE_FAILED\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/pstore-report.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/pstore-report.txt > /run/pstore-report.b64 || continue
  /bin/busybox printf 'XOOM_PSTORE_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/pstore-report.b64
  /bin/busybox printf '\nXOOM_PSTORE_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = FREEZERTEST ]; then
  if [ ! -x /bin/freezer-cycle ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s FREEZERTEST_MISSING\n' "$nonce"
   continue
  fi
  # Frame failures too: the fixed script preserves rollback evidence.
  /bin/busybox sh /bin/freezer-cycle > /run/freezer-test.txt 2>&1
  size=$(/bin/busybox wc -c < /run/freezer-test.txt)
  size=$((size + 0))
  if [ "$size" -le 0 ] || [ "$size" -gt 65536 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s FREEZERTEST_SIZE\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/freezer-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/freezer-test.txt > /run/freezer-test.b64 || continue
  /bin/busybox printf 'XOOM_FREEZERTEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/freezer-test.b64
  /bin/busybox printf '\nXOOM_FREEZERTEST_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = DEVICEPMTEST ]; then
  if [ ! -x /bin/devicepm-cycle ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s DEVICEPMTEST_MISSING\n' "$nonce"
   continue
  fi
  # Frame failures too: the fixed script preserves rollback evidence.
  /bin/busybox sh /bin/devicepm-cycle > /run/devicepm-test.txt 2>&1
  size=$(/bin/busybox wc -c < /run/devicepm-test.txt)
  size=$((size + 0))
  if [ "$size" -le 0 ] || [ "$size" -gt 65536 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s DEVICEPMTEST_SIZE\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/devicepm-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/devicepm-test.txt > /run/devicepm-test.b64 || continue
  /bin/busybox printf 'XOOM_DEVICEPMTEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/devicepm-test.b64
  /bin/busybox printf '\nXOOM_DEVICEPMTEST_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = LP2TEST ]; then
  if [ ! -x /bin/lp2-cycle ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s LP2TEST_MISSING\n' "$nonce"
   continue
  fi
  /bin/busybox sh /bin/lp2-cycle > /run/lp2-test.txt 2>&1
  size=$(/bin/busybox wc -c < /run/lp2-test.txt)
  size=$((size + 0))
  checksum=$(/bin/busybox sha256sum /run/lp2-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/lp2-test.txt > /run/lp2-test.b64 || continue
  /bin/busybox printf 'XOOM_LP2TEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/lp2-test.b64
  /bin/busybox printf '\nXOOM_LP2TEST_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = LP2STATUS ]; then
  [ -f /run/lp2-test.txt ] || { /bin/busybox printf 'XOOM_ERROR_V2 %s LP2STATUS_MISSING\n' "$nonce"; continue; }
  size=$(/bin/busybox wc -c < /run/lp2-test.txt)
  size=$((size + 0))
  checksum=$(/bin/busybox sha256sum /run/lp2-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/lp2-test.txt > /run/lp2-status.b64 || continue
  /bin/busybox printf 'XOOM_LP2STATUS_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/lp2-status.b64
  /bin/busybox printf '\nXOOM_LP2STATUS_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = LATETEST ] || [ "$verb" = SYSCTEST ]; then
  case "$verb" in
   SYSCTEST) stage=syscore ;;
   *) stage=late ;;
  esac
  if [ ! -x "/bin/$stage-cycle" ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s %sTEST_MISSING\n' "$nonce" "$stage"
   continue
  fi
  /bin/busybox sh "/bin/$stage-cycle" > "/run/$stage-test.txt" 2>&1
  size=$(/bin/busybox wc -c < "/run/$stage-test.txt")
  size=$((size + 0))
  checksum=$(/bin/busybox sha256sum "/run/$stage-test.txt") || continue
  checksum=${checksum%% *}
  /bin/busybox base64 "/run/$stage-test.txt" > "/run/$stage-test.b64" || continue
  /bin/busybox printf 'XOOM_%s_V1 %s %s %s\n' "$verb" "$nonce" "$size" "$checksum"
  /bin/busybox cat "/run/$stage-test.b64"
  /bin/busybox printf '\nXOOM_%s_END_V1 %s\n' "$verb" "$nonce"
  continue
 fi
 if [ "$verb" = LATESTATUS ] || [ "$verb" = SYSSTATUS ]; then
  case "$verb" in
   SYSSTATUS) stage=syscore ;;
   *) stage=late ;;
  esac
  [ -f "/run/$stage-test.txt" ] || { /bin/busybox printf 'XOOM_ERROR_V2 %s %sSTATUS_MISSING\n' "$nonce" "$stage"; continue; }
  size=$(/bin/busybox wc -c < "/run/$stage-test.txt")
  size=$((size + 0))
  checksum=$(/bin/busybox sha256sum "/run/$stage-test.txt") || continue
  checksum=${checksum%% *}
  /bin/busybox base64 "/run/$stage-test.txt" > "/run/$stage-status.b64" || continue
  /bin/busybox printf 'XOOM_%s_V1 %s %s %s\n' "$verb" "$nonce" "$size" "$checksum"
  /bin/busybox cat "/run/$stage-status.b64"
  /bin/busybox printf '\nXOOM_%s_END_V1 %s\n' "$verb" "$nonce"
  continue
 fi
 if [ "$verb" = CPU1TEST ]; then
  if [ ! -x /bin/cpu1-cycle ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s CPU1TEST_MISSING\n' "$nonce"
   continue
  fi
  /bin/busybox sh /bin/cpu1-cycle > /run/cpu1-test.txt 2>&1
  size=$(/bin/busybox wc -c < /run/cpu1-test.txt)
  size=$((size + 0))
  if [ "$size" -le 0 ] || [ "$size" -gt 65536 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s CPU1TEST_SIZE\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/cpu1-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/cpu1-test.txt > /run/cpu1-test.b64 || continue
  /bin/busybox printf 'XOOM_CPU1TEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/cpu1-test.b64
  /bin/busybox printf '\nXOOM_CPU1TEST_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = DPMSTATUS ]; then
  if [ ! -f /run/dpm-test.txt ]; then
   if [ -r /sys/power/wingray_dpm_test ]; then
    /bin/busybox cat /sys/power/wingray_dpm_test > /run/dpm-test.txt
   else
    /bin/busybox printf 'XOOM_ERROR_V2 %s DPMSTATUS_MISSING\n' "$nonce"
    continue
   fi
  fi
  size=$(/bin/busybox wc -c < /run/dpm-test.txt)
  size=$((size + 0))
  checksum=$(/bin/busybox sha256sum /run/dpm-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/dpm-test.txt > /run/dpm-status.b64 || continue
  /bin/busybox printf 'XOOM_DPMSTATUS_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/dpm-status.b64
  /bin/busybox printf '\nXOOM_DPMSTATUS_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = DPMTEST ]; then
  if [ ! -x /bin/dpm-cycle ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s DPMTEST_MISSING\n' "$nonce"
   continue
  fi
  # USB may disappear while devices are suspended; frame the result after resume.
  /bin/busybox sh /bin/dpm-cycle > /run/dpm-test.txt 2>&1
  size=$(/bin/busybox wc -c < /run/dpm-test.txt)
  size=$((size + 0))
  if [ "$size" -le 0 ] || [ "$size" -gt 65536 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s DPMTEST_SIZE\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/dpm-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/dpm-test.txt > /run/dpm-test.b64 || continue
  /bin/busybox printf 'XOOM_DPMTEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/dpm-test.b64
  /bin/busybox printf '\nXOOM_DPMTEST_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = WAKETEST ]; then
  if [ ! -x /bin/wake-arm-cycle ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s WAKETEST_MISSING\n' "$nonce"
   continue
  fi
  # Frame failures too: the fixed script preserves rollback evidence.
  /bin/busybox sh /bin/wake-arm-cycle > /run/wake-arm-test.txt 2>&1
  size=$(/bin/busybox wc -c < /run/wake-arm-test.txt)
  size=$((size + 0))
  if [ "$size" -le 0 ] || [ "$size" -gt 65536 ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s WAKETEST_SIZE\n' "$nonce"
   continue
  fi
  checksum=$(/bin/busybox sha256sum /run/wake-arm-test.txt) || continue
  checksum=${checksum%% *}
  /bin/busybox base64 /run/wake-arm-test.txt > /run/wake-arm-test.b64 || continue
  /bin/busybox printf 'XOOM_WAKETEST_V1 %s %s %s\n' "$nonce" "$size" "$checksum"
  /bin/busybox cat /run/wake-arm-test.b64
  /bin/busybox printf '\nXOOM_WAKETEST_END_V1 %s\n' "$nonce"
  continue
 fi
 if [ "$verb" = FBTEST ] || [ "$verb" = DCTEST ]; then
  if [ ! -x /bin/fb-blank-test ]; then
   /bin/busybox printf 'XOOM_ERROR_V2 %s FBTEST_MISSING\n' "$nonce"
   continue
  fi
  if [ "$verb" = DCTEST ]; then
   /bin/busybox sh /bin/fb-blank-test --dc > /run/fb-blank-test.txt 2>&1
  else
   /bin/busybox sh /bin/fb-blank-test > /run/fb-blank-test.txt 2>&1
  fi
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
