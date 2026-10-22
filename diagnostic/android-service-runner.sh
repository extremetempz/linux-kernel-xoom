#!/bin/busybox sh
# Experimental image-30 service runner; arguments come only from generated init.
# Keep inherited property workspace/socket descriptors and the Android environment.
name=$1
shift
case "$name" in
 healthd|servicemanager|vold|netd|debuggerd|surfaceflinger|zygote|drm|media|keystore|installd|sdcard) ;;
 *) exit 126;;
esac
exec "$@" > "/run/android-logs/$name/stdout.txt" 2>&1
