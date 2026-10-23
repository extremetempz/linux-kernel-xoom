#!/bin/busybox sh
# Fixed read-only CPU/cache/clock and memory metadata. No control writes,
# arbitrary register reads, clock changes, allocation tests or purge operations.
echo XOOM_SOC_BEGIN
case "$(/bin/busybox uname -r)" in
 4.4.147-wingray-android44-touch|4.4.147-wingray-android44-l2|4.4.147-wingray-android44-smp|4.4.147-wingray-android44-smp2|4.4.147-wingray-android44-smptrace) ;;
 *) echo XOOM_SOC_DENIED_RELEASE; echo XOOM_SOC_END; exit 0;;
esac
if ! /bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx motorola,wingray; then
 echo XOOM_SOC_DENIED_BOARD; echo XOOM_SOC_END; exit 0
fi
read_fixed() {
 echo "XOOM_SOC_FILE $1"
 if [ -r "$1" ]; then /bin/busybox head -c "$2" "$1"; echo
 else echo unavailable
 fi
}
for attr in family soc_id revision; do read_fixed "/sys/devices/soc0/$attr" 128; done
for attr in possible present online offline; do read_fixed "/sys/devices/system/cpu/$attr" 64; done
read_fixed /proc/cpuinfo 2048
for cpu in 0 1; do
 for attr in scaling_driver scaling_cur_freq cpuinfo_cur_freq scaling_min_freq scaling_max_freq scaling_available_frequencies; do
  read_fixed "/sys/devices/system/cpu/cpu$cpu/cpufreq/$attr" 128
 done
 for index in 0 1 2; do
  for attr in level type size coherency_line_size ways_of_associativity; do
   read_fixed "/sys/devices/system/cpu/cpu$cpu/cache/index$index/$attr" 64
  done
 done
done
for clock in cclk pll_x pll_p emc; do read_fixed "/sys/kernel/debug/clk/$clock/clk_rate" 64; done
read_fixed /proc/meminfo 4096
read_fixed /proc/vmstat 4096
for attr in adj minfree; do read_fixed "/sys/module/lowmemorykiller/parameters/$attr" 128; done
echo XOOM_SOC_END
