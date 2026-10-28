#!/bin/busybox sh
# One root-only kernel task-freezer test. Never writes a sleep state.
BB=/bin/busybox
TEST=/sys/power/wingray_freezer_test
echo XOOM_FREEZER_TEST_V1
finish()
{
 rc=$?
 trap - EXIT HUP INT TERM
 [ ! -e "$TEST" ] || echo "FREEZERTEST_EXIT_STATUS $("$BB" cat "$TEST" 2>&1)"
 echo "FREEZERTEST_PROCESS_RC $rc"
 echo XOOM_FREEZER_TEST_END
 exit "$rc"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$#" -eq 0 ] && [ "$("$BB" id -u)" = 0 ] || exit 1
[ -f "$TEST" ] || { echo FREEZERTEST_MISSING; exit 1; }
before=$("$BB" cat "$TEST") || exit 1
echo "FREEZERTEST_BEFORE $before"
count=${before#completed=}
count=${count%% *}
case "$count" in ''|*[!0-9]*) exit 1;; esac
[ "$before" = "completed=$count last_result=0 device_suspend=0 cpu_sleep=0 ordinary_sleep=blocked" ] || exit 1
[ "$count" -lt 4294967295 ] || exit 1
expected=$((count + 1))
echo 1 > "$TEST"
rc=$?
echo "FREEZERTEST_WRITE_RC $rc"
after=$("$BB" cat "$TEST") || exit 1
echo "FREEZERTEST_AFTER $after"
[ "$rc" -eq 0 ] || exit 1
[ "$after" = "completed=$expected last_result=0 device_suspend=0 cpu_sleep=0 ordinary_sleep=blocked" ] || exit 1
echo FREEZERTEST_COUNTER_ADVANCED_1
exit 0
