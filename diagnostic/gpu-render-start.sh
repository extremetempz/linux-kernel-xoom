#!/bin/busybox sh
# One disposable child only. Never preload PID1, a reporter or a service.
exec > /run/gpu-render-result.txt 2>&1
echo XOOM_GPU_RENDER_BEGIN
echo "XOOM_GPU_KERNEL $(/bin/busybox uname -r)"
if [ -z "$ANDROID_PROPERTY_WORKSPACE" ]; then
 echo XOOM_GPU_RENDER_FAILED_NO_PROPERTY_WORKSPACE
 exit 1
fi
echo XOOM_GPU_PROPERTY_WORKSPACE_PRESENT
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
if [ "$ready" -ne 1 ]; then
 /bin/busybox ls -l /dev/nv* /dev/tegra_sema
 echo XOOM_GPU_RENDER_FAILED_MISSING_NODES
 exit 2
fi
echo XOOM_GPU_RENDER_DEVICES_READY
/bin/busybox cat /proc/interrupts > /run/gpu-interrupts-before.txt
/bin/busybox timeout -s KILL 35 /bin/busybox env XOOM_EGL_PROBE_CHILD=1 LD_PRELOAD=/system/lib/xoom-egl-probe.so /system/bin/sh -c : > /run/gpu-probe-output.txt 2>&1
result=$?
/bin/busybox cat /run/gpu-probe-output.txt
/bin/busybox cat /proc/interrupts > /run/gpu-interrupts-after.txt
echo "XOOM_GPU_RENDER_EXIT $result"
if [ "$result" -eq 0 ] && /bin/busybox grep -q '^XOOM_EGL_OFFSCREEN_READBACK_PASS' /run/gpu-probe-output.txt; then
 echo XOOM_GPU_RENDER_PASS
else
 echo XOOM_GPU_RENDER_FAILED
fi
echo XOOM_GPU_RENDER_DONE
