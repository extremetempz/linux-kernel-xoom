#!/bin/busybox sh
# Validation-only recovery: no Android/TWRP, physical filesystem mounts or RW release.
export PATH=/bin
unset LD_LIBRARY_PATH
umask 077
fail() {
 echo "XOOM_OFFLINE97_FAILED_$1" > /dev/kmsg
 echo "failed_$1" > /run/offline97-state 2>/dev/null
 while :; do /bin/busybox sleep 5; done
}
/bin/busybox mount -t proc proc /proc || fail proc
/bin/busybox mount -t sysfs sysfs /sys || fail sysfs
/bin/busybox mount -t devtmpfs devtmpfs /dev || fail devtmpfs
/bin/busybox mkdir -p /run /tmp /dev/pts || fail directories
/bin/busybox mount -t tmpfs -o size=128m,mode=0700,nosuid,nodev tmpfs /run || fail ram_run
/bin/busybox mount -t tmpfs -o size=8m,mode=0700,nosuid,nodev tmpfs /tmp || fail ram_tmp
/bin/busybox mount -t devpts devpts /dev/pts || fail pts
/bin/busybox sh /bin/usb-report-loop > /run/usb-loop-errors.txt 2>&1 &
echo preparing > /run/offline97-state
/bin/busybox dd if=/bin/e2fsck of=/run/e2fsck bs=4096 2>/dev/null || fail checker_copy
/bin/busybox chmod 0755 /run/e2fsck || fail checker_chmod
got=$(/bin/busybox sha256sum /run/e2fsck); got=${got%% *}
[ "$got" = b063d57f8bdd3c8474a6ad3ad69faa13dfac3e17d251da50557052b07096d171 ] || fail checker_copy_hash
echo running > /run/offline97-state
/bin/busybox timeout -s KILL 60 /bin/busybox sh /bin/offline97-ramtest > /run/offline97-ramtest.txt 2>&1
rc=$?
echo "RAMTEST_EXIT $rc" >> /run/offline97-ramtest.txt
if [ "$rc" = 0 ]; then echo passed > /run/offline97-state; else echo failed > /run/offline97-state; fi
while :; do /bin/busybox sleep 5; done
