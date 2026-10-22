#!/bin/busybox sh
# DRAFT: incomplete Android image-30 integration; do not deploy directly.
# See docs/android44-lockscreen-checkpoint.md for missing generation and validation.
# Arguments originate only in the generated, audited init.rc, never USB input.
name=$1
shift
case "$name" in
 healthd|servicemanager|vold|netd|debuggerd|surfaceflinger|zygote|drm|media|keystore|installd|sdcard) ;;
 *) exit 126;;
esac
exec "$@" > "/run/android-logs/$name/stdout.txt" 2>&1
