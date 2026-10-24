#!/bin/busybox sh
echo XOOM_GPU_REPORT_BEGIN
for file in gpu-render-result.txt gpu-interrupts-before.txt gpu-interrupts-after.txt; do
 echo "XOOM_GPU_FILE $file"
 [ ! -r "/run/$file" ] || /bin/busybox head -c 32768 "/run/$file"
done
/bin/busybox ls -l /dev/nvmap /dev/nvhost-ctrl /dev/nvhost-gr2d /dev/nvhost-gr3d /dev/tegra_sema
[ ! -r /sys/kernel/debug/clk/clk_summary ] || /bin/busybox head -c 32768 /sys/kernel/debug/clk/clk_summary
echo XOOM_GPU_REPORT_END
