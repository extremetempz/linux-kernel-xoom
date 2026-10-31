#!/bin/busybox sh
# One root-only late PM stage test. No platform/LP2 entry.
BB=/bin/busybox
TEST=/sys/power/wingray_late_test
echo XOOM_LATETEST_V1
finish()
{
 rc=$?
 trap - EXIT HUP INT TERM
 [ ! -e "$TEST" ] || echo "LATETEST_EXIT_STATUS $("$BB" cat "$TEST" 2>&1)"
 echo "LATETEST_PROCESS_RC $rc"
 echo XOOM_LATETEST_END
 exit "$rc"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$#" -eq 0 ] && [ "$("$BB" id -u)" = 0 ] || exit 1
[ -f "$TEST" ] || { echo LATETEST_MISSING; exit 1; }
before=$("$BB" cat "$TEST") || exit 1
echo "LATETEST_BEFORE $before"
count=${before#completed=}
count=${count%% *}
case "$count" in ''|*[!0-9]*) exit 1;; esac
expected=$((count + 1))
echo 1 > "$TEST"
rc=$?
echo "LATETEST_WRITE_RC $rc"
after=$("$BB" cat "$TEST") || exit 1
echo "LATETEST_AFTER $after"
[ "$rc" -eq 0 ] || exit 1
[ "$after" = "completed=$expected last_result=0 selected=late whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked" ] || exit 1
echo LATETEST_COUNTER_ADVANCED_1
exit 0
