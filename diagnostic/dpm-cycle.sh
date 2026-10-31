#!/bin/busybox sh
# One root-only full-tree devices-only DPM test. Never writes a sleep state.
BB=/bin/busybox
TEST=/sys/power/wingray_dpm_test
echo XOOM_DPM_TEST_V1
finish()
{
 rc=$?
 trap - EXIT HUP INT TERM
 [ ! -e "$TEST" ] || echo "DPMTEST_EXIT_STATUS $("$BB" cat "$TEST" 2>&1)"
 echo "DPMTEST_PROCESS_RC $rc"
 echo XOOM_DPM_TEST_END
 exit "$rc"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$#" -eq 0 ] && [ "$("$BB" id -u)" = 0 ] || exit 1
[ -f "$TEST" ] || { echo DPMTEST_MISSING; exit 1; }
before=$("$BB" cat "$TEST") || exit 1
echo "DPMTEST_BEFORE $before"
count=${before#completed=}
count=${count%% *}
case "$count" in ''|*[!0-9]*) exit 1;; esac
[ "$before" = "completed=$count last_result=0 selected=dpm whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked" ] || exit 1
[ "$count" -lt 4294967295 ] || exit 1
expected=$((count + 1))
echo 1 > "$TEST"
rc=$?
echo "DPMTEST_WRITE_RC $rc"
after=$("$BB" cat "$TEST") || exit 1
echo "DPMTEST_AFTER $after"
[ "$rc" -eq 0 ] || exit 1
[ "$after" = "completed=$expected last_result=0 selected=dpm whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked" ] || exit 1
echo DPMTEST_COUNTER_ADVANCED_1
exit 0
