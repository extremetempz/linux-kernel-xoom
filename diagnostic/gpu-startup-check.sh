#!/bin/busybox sh
# Startup control only: never load the EGL probe or submit GPU work.
exec > /run/gpu-render-result.txt 2>&1
mark() {
 [ ! -c /dev/xoom-startup-trace ] || /bin/busybox printf '%s\n' "$1" > /dev/xoom-startup-trace
}
mark 3
echo XOOM_GPU_STARTUP_ONLY_BEGIN
/bin/busybox uname -r
if [ -n "$ANDROID_PROPERTY_WORKSPACE" ]; then
 echo XOOM_GPU_PROPERTY_WORKSPACE_PRESENT
else
 echo XOOM_GPU_PROPERTY_WORKSPACE_MISSING
fi
waited=0
while [ "$waited" -lt 20 ]; do
 ready=1
 for node in nvmap nvhost-ctrl nvhost-gr2d nvhost-gr3d tegra_sema; do
  [ -c "/dev/$node" ] || ready=0
 done
 [ "$ready" -eq 1 ] && break
 /bin/busybox sleep 1
 waited=$((waited + 1))
done
if [ "$ready" -eq 1 ]; then
 mark 4
 echo XOOM_GPU_STARTUP_DEVICES_READY
else
 mark 5
 echo XOOM_GPU_STARTUP_DEVICES_MISSING
fi
echo XOOM_GPU_RENDER_SKIPPED_STARTUP_TRACE
echo XOOM_GPU_STARTUP_ONLY_DONE
