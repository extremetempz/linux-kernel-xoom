#!/bin/busybox sh
# One root-only CPU1 offline/online test. CPU0 is never offlined.
BB=/bin/busybox
CPU=/sys/devices/system/cpu/cpu1/online
echo XOOM_CPU1_TEST_V1
finish()
{
 rc=$?
 trap - EXIT HUP INT TERM
 echo "CPU1TEST_ONLINE_AFTER $("$BB" cat /sys/devices/system/cpu/online 2>&1)"
 echo "CPU1TEST_PROCESS_RC $rc"
 echo XOOM_CPU1_TEST_END
 exit "$rc"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$#" -eq 0 ] && [ "$("$BB" id -u)" = 0 ] || exit 1
[ -w "$CPU" ] || { echo CPU1TEST_NOT_WRITABLE; exit 1; }
before=$("$BB" cat /sys/devices/system/cpu/online) || exit 1
echo "CPU1TEST_ONLINE_BEFORE $before"
case "$before" in *0-1*) ;; *) echo CPU1TEST_CPU1_NOT_ONLINE; exit 1;; esac
echo 0 > "$CPU" || { echo CPU1TEST_OFFLINE_WRITE_FAILED; exit 1; }
sleep 1
[ "$("$BB" cat "$CPU")" = 0 ] || { echo CPU1TEST_CPU1_STILL_ONLINE; exit 1; }
echo CPU1TEST_CPU1_OFFLINE
echo 1 > "$CPU" || { echo CPU1TEST_ONLINE_WRITE_FAILED; exit 1; }
i=0
while [ "$i" -lt 10 ]; do
 [ "$("$BB" cat "$CPU")" = 1 ] && break
 sleep 1
 i=$((i+1))
done
[ "$("$BB" cat "$CPU")" = 1 ] || { echo CPU1TEST_CPU1_DID_NOT_RETURN; exit 1; }
after=$("$BB" cat /sys/devices/system/cpu/online) || exit 1
echo "CPU1TEST_ONLINE_AFTER $after"
case "$after" in *0-1*) ;; *) echo CPU1TEST_CPU1_NOT_ONLINE_AFTER; exit 1;; esac
echo CPU1TEST_PASS
exit 0
