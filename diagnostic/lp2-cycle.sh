#!/bin/busybox sh
# One root-only genuine LP2 request. No automatic retry; the write blocks until wake.
BB=/bin/busybox
TEST=/sys/power/wingray_lp2_test
echo XOOM_LP2TEST_V1
finish()
{
 rc=$?
 trap - EXIT HUP INT TERM
 [ ! -e "$TEST" ] || echo "LP2TEST_EXIT_STATUS $("$BB" cat "$TEST" 2>&1)"
 echo "LP2TEST_PROCESS_RC $rc"
 echo XOOM_LP2TEST_END
 exit "$rc"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$#" -eq 0 ] && [ "$("$BB" id -u)" = 0 ] || exit 1
[ -f "$TEST" ] || { echo LP2TEST_MISSING; exit 1; }
before=$("$BB" cat "$TEST") || exit 1
echo "LP2TEST_BEFORE $before"
echo 1 > "$TEST"
rc=$?
echo "LP2TEST_WRITE_RC $rc"
after=$("$BB" cat "$TEST") || exit 1
echo "LP2TEST_AFTER $after"
[ "$rc" -eq 0 ] || exit 1
echo LP2TEST_RETURNED
exit 0
