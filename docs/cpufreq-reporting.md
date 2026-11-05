# Tegra20 CPU frequency reporting — diagnosis and build

## Decatf reference

Decatf's `android-4.4-p4wifi` uses the same
`drivers/cpufreq/tegra20-cpufreq.c` static PLLX table and registers the same
`cclk`, `pll_x`, `pll_p` and `emc` clocks. Its `tegra_android_defconfig` enables:

```text
CONFIG_CPU_FREQ=y
CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y
CONFIG_ARM_TEGRA20_CPUFREQ=y
```

The Samsung DTS supplies `cpu-supply`/`core-supply`; the static Tegra20 driver
does not consume those regulators. They are therefore not copied to Wingray.

## Xoom difference

The driver already exists in the Wingray tree, including:

- 216 MHz–1.5 GHz table;
- Wingray filter marking entries above 1 GHz invalid;
- `policy->max = 1000000`;
- cclk/pll_x/pll_p/emc clock lookups.

Every Wingray defconfig had:

```text
# CONFIG_CPU_FREQ is not set
```

That is the exact reason no cpufreq policy, `scaling_cur_freq`, or frequency
table was exposed and Android displayed 0 MHz.

## Minimal change

`kernel/patches/0184-wingray-enable-tegra20-cpufreq.patch`:

1. Enables CPU_FREQ, the existing Tegra20 driver, statistics and governors.
2. Selects the **performance** governor by default so reporting is validated
   without dynamic voltage/frequency transitions.
3. Allows CPU_FREQ to coexist with the fixed-clock
   `TEGRA_GRHOST_WINGRAY_GPU_TEST` profile.
4. Skips cpufreq's EMC rate votes when the GPU test owns fixed EMC timing.

No voltage table, regulator value, overclock point, or thermal limit was added.
CPU1 uses its own cpufreq policy against the shared CPU clock; no independent
clock hardware was invented.

## Diagnostic image

`artifacts/cpufreq-ready/wingray-android44-persistent.img`

- 4,253,696 bytes
- SHA256 `af839b36410b8e0631624c53923d69302d7896148f199bd93856d4b8f9aa79ec`
- Boot audit passed.
- Not flashed.

## Hardware validation

Flash only after explicit approval:

```sh
fastboot flash boot \
  /home/justin/linux-kernel-xoom/cpufreq-review/artifacts/cpufreq-ready/wingray-android44-persistent.img
fastboot reboot
```

Boot Android, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/storage-cpufreq-report1 \
  --storage-mode android44-persistent
```

Read:

```sh
sed -n '/XOOM_CPUFREQ_BEGIN/,/XOOM_CPUFREQ_END/p' \
  artifacts/storage-cpufreq-report1/report-private.txt
```

Required:

- cpu0 and cpu1 `scaling_cur_freq` nonzero;
- `cpuinfo_max_freq=1000000`;
- `cpuinfo_min_freq=216000`;
- available frequencies no higher than 1000000;
- `scaling_governor=performance`;
- no cpufreq probe errors in dmesg.

Do not enable dynamic governors or alter voltages until this reporting passes.
