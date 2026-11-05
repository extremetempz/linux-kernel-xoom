# Opt-in 1.7 GHz CPU support — TeamEOS-derived, unvalidated

## TeamEOS reference

TeamEOS's 3.1 kernel uses `tegra2_dvfs.c`, `cpu-tegra.c`, and
`tegra2_clocks.c`:

- CPU process 0/1 tables through 1700 MHz at 1400 mV;
- core rail kept 50 mV above CPU, 1450 mV maximum;
- RTC/aon 1300 mV maximum;
- max8649 `vdd_cpu` 770–1400 mV;
- PLLX 1.7 GHz entries;
- cpufreq governors: performance, powersave, userspace, ondemand,
  interactive, conservative.

## Integration in the 4.4 Xoom tree

The existing `drivers/staging/tegra/tegra20-dvfs.c` is now used instead of
writing a new voltage driver.

The Android DTS intentionally omits the full peripheral wrapper
(`WINGRAY_EARLY_BOOT`). The overclock image therefore adds only the required
power nodes to `tegra20-motorola-wingray-gpu-test.dts`:

- max8649 `vdd_cpu` at 0x60, 770–1400 mV;
- CPCAP SW2 `core`, 1000–1450 mV;
- CPCAP SW4 `aon`, 1000–1300 mV;
- `tegra20-dvfs` node with CPU/core/RTC supplies and clocks.

DVFS is now linked with the fixed-clock GPU profile; cpufreq EMC votes remain
disabled in that profile.

CPU tables add 1700 MHz at 1400 mV. The default policy remains **1 GHz**, so
booting is not overclocked. A root user can opt in through standard sysfs.

## Image

`artifacts/cpufreq-oc6-ready/wingray-android44-persistent.img`

- 4,255,744 bytes
- SHA256 `9773a6afe42137058dc665ffab3639fdb4ccad002aa63fb07e65f19c202e0a02`
- Boot audit passed.
- Not flashed.

## Required staged hardware validation

Boot first and capture. Do not set 1.7 GHz until all checks below pass.

```sh
fastboot flash boot \
  /home/justin/linux-kernel-xoom/cpufreq-review/artifacts/cpufreq-oc6-ready/wingray-android44-persistent.img
fastboot reboot
```

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/storage-cpufreq-oc1 \
  --storage-mode android44-persistent
```

Verify:

```text
XOOM_CPUFREQ_BEGIN
CPU 0/1 scaling_cur_freq 1000000
available ... 1600000 1700000
XOOM_DVFS_BEGIN
CPU voltage = ...
RTC voltage = ...
Core voltage = ...
```

Also check dmesg:

```sh
grep -E 'tegra_dvfs_probe|Can.t get CPU regulator|cpu_process_id' \
  artifacts/storage-cpufreq-oc1/report-private.txt
```

`cpu_process_id` must be 0 or 1. Do not raise frequency if DVFS debugfs is
absent, the clock names fail, or regulators are missing.

## Raise frequency one step at a time

Use a root shell on the device:

```sh
echo 1200000 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
cat /sys/kernel/debug/tegra_dvfs
```

Then test 1400000, 1600000 and finally 1700000. After each step:

- confirm `scaling_cur_freq` matches;
- confirm CPU voltage rises in `tegra_dvfs`;
- run a sustained load and check temperature/battery current;
- revert immediately on instability.

```sh
echo 1000000 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
```

The policy is shared, and default performance governor means max-frequency
writes take effect for both CPUs.

## Limits

- PLLX 1.7 GHz entries are adapted from TeamEOS but not hardware-validated.
- No thermal throttle exists in this kernel.
- CPU process IDs other than 0/1 are not covered by the DVFS table.
- Core/RTC voltage changes may affect GPU, display and USB.
- 1.7 GHz is overclocking and can crash, overheat, or corrupt data.
- Do not enable dynamic governors until staged validation passes.
