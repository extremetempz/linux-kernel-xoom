#!/usr/bin/env python3
"""Offline gate for reused Tegra20 cpufreq reporting and GPU coexistence."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
cfg=(R/'sources/kernel-donor/arch/arm/configs/wingray_android44_persistent_defconfig').read_text()
for key in ('CPU_FREQ','ARM_TEGRA20_CPUFREQ','CPU_FREQ_DEFAULT_GOV_PERFORMANCE','TEGRA_GRHOST_WINGRAY_GPU_TEST','TEGRA_DOWNSTREAM'):
    assert 'CONFIG_'+key+'=y\n' in cfg,key
assert 'CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y\n' not in cfg
assert '# CONFIG_CPU_FREQ is not set' not in cfg
k=(R/'sources/kernel-donor/drivers/cpufreq/tegra20-cpufreq.c').read_text()
assert 'clk_get_sys(NULL, "cclk")' in k and 'clk_get_sys(NULL, "pll_x")' in k
assert 'cpufreq_generic_init' in k and 'policy->max = 1000000' in k
assert '{ .frequency = 1700000 }' in k
assert '#ifndef CONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST' in k
kconfig=(R/'sources/kernel-donor/drivers/staging/tegra/video/Kconfig').read_text()
assert 'config TEGRA_GRHOST_WINGRAY_GPU_TEST' in kconfig
assert 'depends on !CPU_FREQ' not in kconfig.split('config TEGRA_GRHOST_WINGRAY_GPU_TEST',1)[1].split('config ',1)[0]
d=(R/'sources/kernel-donor/drivers/staging/tegra/tegra20-dvfs.c').read_text()
assert 'CPU_MAX_VDD    1400' in d and '1400,  // 1700 MHz' in d
assert 'CORE_MAX_VDD (1450)' in d
pll=(R/'sources/kernel-donor/drivers/clk/tegra/clk-tegra20.c').read_text()
assert '1700000000' in pll
board=(R/'sources/kernel-donor/arch/arm/boot/dts/tegra20-motorola-wingray-gpu-test.dts').read_text()
assert 'compatible = "tegra20-dvfs"' in board
assert 'regulator-max-microvolt = <1400000>' in board
assert 'regulator-max-microvolt = <1450000>' in board
assert 'compatible = "maxim,max8649"' in board
report=(R/'diagnostic/android44-gpu-report.sh').read_text()
for token in ('XOOM_CPUFREQ_BEGIN','scaling_cur_freq','cpuinfo_max_freq','policy','cclk'):
    assert token in report,token
print('PASS: existing Tegra20 cpufreq is enabled, capped, reported, and coexists with the fixed-clock GPU profile')
