#!/usr/bin/env python3
"""Source gate for the isolated, manual-only Image93 LP2 candidate."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
K=ROOT/'sources/kernel-donor'
cfg=(K/'arch/arm/configs/wingray_android44_lp2test_defconfig').read_text()
dts=(K/'arch/arm/boot/dts/tegra20-motorola-wingray-android44-lp2.dts').read_text()
sus=(K/'kernel/power/suspend.c').read_text()
main=(K/'kernel/power/main.c').read_text()
pmc=(K/'drivers/soc/tegra/pmc.c').read_text()
pm=(K/'arch/arm/mach-tegra/pm.c').read_text()
cpcap=(K/'drivers/mfd/motorola-cpcap.c').read_text()
hdr=(K/'include/linux/wingray_pm_prepare.h').read_text()
assert 'CONFIG_MOTOROLA_WINGRAY_LP2_TEST=y\n' in cfg
assert 'CONFIG_MOTOROLA_WINGRAY_DPM_TEST=y\n' not in cfg
assert 'CONFIG_MOTOROLA_WINGRAY_DEVICEPM_TEST=y\n' in cfg
assert 'CONFIG_MOTOROLA_WINGRAY_PM_PREPARE=y\n' in cfg
assert 'CONFIG_PM_AUTOSLEEP=y' not in cfg and 'CONFIG_PM_WAKELOCKS=y' not in cfg
assert 'CONFIG_CPU_FREQ is not set' in cfg
assert 'nvidia,suspend-mode = <2>' in dts
assert 'nvidia,cpu-pwr-good-time = <1500>' in dts
assert 'nvidia,cpu-pwr-off-time = <1>' in dts
assert 'nvidia,core-power-req-active-high' in dts
assert 'nvidia,sys-clock-req-active-high' in dts
assert 'CONFIG_MOTOROLA_WINGRAY_LP2_TEST' in hdr and 'wingray_pm_lp2_test_active' in hdr
# Ordinary suspension remains blocked unless the root-only manual gate is armed.
start=sus.index('int pm_suspend(suspend_state_t state)')
end=sus.index('EXPORT_SYMBOL(pm_suspend)',start)
body=sus[start:end]
assert body.index('wingray_pm_prepare_only()') < body.index('wingray_pm_lp2_test_active()')
assert 'wingray_pm_lp2_test_set_active(true)' in main
assert 'pm_suspend(PM_SUSPEND_MEM)' in main
# Real Tegra ops must be registered; no dummy DPM ops in this profile.
assert 'wingray_test_suspend_ops' in pm
assert 'suspend_set_ops(&tegra_suspend_ops)' in pm
# PMC core request/timer support and original Motorola values.
assert 'PMC_CNTRL_PWRREQ_OE' in pmc and 'PMC_COREPWRGOOD_TIMER' in pmc
assert 'outer_flush_all();' in pm and 'outer_disable();' in pm
assert 'cpu_pm_enter();' in pm and 'cpu_cluster_pm_enter();' in pm
assert 'wingray_pm_lp2_test_active()' in cpcap
assert 'cpu_power' not in cfg
print('PASS isolated LP2 candidate source gates; no hardware sleep claim')
