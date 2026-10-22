#!/bin/busybox sh
# DRAFT: incomplete Android image-30 integration; do not deploy directly.
# See docs/android44-lockscreen-checkpoint.md for missing generation and validation.
# Fixed framed requests only. Survives PID1 exec; no interactive shell.
echo -1000 > /proc/self/oom_score_adj
while :; do
 if [ -c /dev/ttyGS0 ]; then
  /bin/busybox sh /bin/diagnostic-server < /dev/ttyGS0 > /dev/ttyGS0 2>/run/diagnostic-server-errors.txt
 fi
 /bin/busybox sleep 1
done
