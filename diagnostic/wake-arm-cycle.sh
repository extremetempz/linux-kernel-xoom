#!/bin/busybox sh
# One fixed awake-only parent wake-reference test. Never requests system sleep.
BB=/bin/busybox
ARM=
armed=0
echo XOOM_WAKE_ARM_TEST_V1
finish()
{
 rc=$?
 trap - EXIT HUP INT TERM
 if [ -n "$ARM" ]; then
  echo "WAKETEST_EXIT_STATUS $("$BB" cat "$ARM" 2>&1)"
 fi
 if [ "$armed" -eq 1 ]; then
  echo 0 > "$ARM"
  cleanup=$?
  echo "WAKETEST_CLEANUP_RC $cleanup"
  echo "WAKETEST_CLEANUP_AFTER $("$BB" cat "$ARM" 2>&1)"
  [ "$cleanup" -eq 0 ] || rc=1
 fi
 echo "WAKETEST_PROCESS_RC $rc"
 echo XOOM_WAKE_ARM_TEST_END
 exit "$rc"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
[ "$#" -eq 0 ] && [ "$("$BB" id -u)" = 0 ] || exit 1
count=0
for f in /sys/bus/spi/devices/*/wingray_wake_arm; do
 [ -f "$f" ] || continue
 ARM=$f
 count=$((count + 1))
done
[ "$count" -eq 1 ] || { echo WAKETEST_MISSING_OR_AMBIGUOUS; exit 1; }
before=$("$BB" cat "$ARM") || exit 1
echo "WAKETEST_BEFORE $before"
[ "$before" = 'owned=0 parent_wake=0 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked' ] || exit 1
# Mark the attempted acquisition before writing: a failed post-check may
# leave ownership for cleanup/retry, as reported by the driver.
armed=1
echo 1 > "$ARM"
rc=$?
echo "WAKETEST_ARM_RC $rc"
[ "$rc" -eq 0 ] || exit 1
after=$("$BB" cat "$ARM") || exit 1
echo "WAKETEST_ARMED $after"
[ "$after" = 'owned=1 parent_wake=1 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked' ] || exit 1
echo 0 > "$ARM"
rc=$?
echo "WAKETEST_DISARM_RC $rc"
[ "$rc" -eq 0 ] || exit 1
armed=0
after=$("$BB" cat "$ARM") || exit 1
echo "WAKETEST_AFTER $after"
[ "$after" = 'owned=0 parent_wake=0 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked' ] || exit 1
exit 0
