#!/bin/busybox sh
# Experimental image-30 reporter; package only with prepare-android44.py.
# Fixed framed requests only. Survives PID1 exec; no interactive shell.
echo -1000 > /proc/self/oom_score_adj
while :; do
 if [ -c /dev/ttyGS0 ]; then
  /bin/busybox sh /bin/diagnostic-server < /dev/ttyGS0 > /dev/ttyGS0 2>/run/diagnostic-server-errors.txt
 fi
 /bin/busybox sleep 1
done
