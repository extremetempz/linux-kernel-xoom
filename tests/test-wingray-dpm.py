#!/usr/bin/env python3
"""Image91 staged DPM source gates: full device order, no platform sleep."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
K = ROOT / 'sources/kernel-donor'
suspend = (K / 'kernel/power/suspend.c').read_text()
header = (K / 'include/linux/wingray_pm_prepare.h').read_text()
main = (K / 'kernel/power/main.c').read_text()
cpcap = (K / 'drivers/mfd/motorola-cpcap.c').read_text()
pmc = (K / 'drivers/soc/tegra/pmc.c').read_text()
pm = (K / 'arch/arm/mach-tegra/pm.c').read_text()
timer = (K / 'drivers/clocksource/tegra20_timer.c').read_text()
kconfig = (K / 'arch/arm/mach-tegra/Kconfig').read_text()
config = (K / 'arch/arm/configs/wingray_android44_devicepm91_defconfig').read_text()

assert 'config MOTOROLA_WINGRAY_DPM_TEST' in kconfig
assert 'CONFIG_MOTOROLA_WINGRAY_DPM_TEST=y\n' in config
assert 'WINGRAY_PM_TEST_DPM' in header and 'wingray_pm_dpm_test_active' in header
assert 'if (wingray_pm_prepare_only() && !wingray_pm_dpm_test_active())' in suspend
assert 'pm_test_level = TEST_DEVICES;' in suspend
assert 'suspend_devices_and_enter(PM_SUSPEND_FREEZE)' in suspend
assert 'platform_entry=0 cpu_sleep=0' in suspend
assert 'int pm_suspend(suspend_state_t state)' in suspend
# Ordinary entry still refuses before any tasks/devices change.
start = suspend.index('int pm_suspend(suspend_state_t state)')
assert suspend.index('wingray_pm_prepare_only()', start) < suspend.index('enter_state(state, WINGRAY_PM_TEST_NONE)', start)
assert 'wingray_dpm_test' in main and 'whole_tree=1' in main
# CPCAP selected-callback path and genuine DPM share only the checked arm helper.
assert 'wingray_pm_dpm_test_active()' in cpcap
assert 'cpcap_wingray_set_wake_arm(cpcap, true)' in cpcap
assert 'cpcap_wingray_set_wake_arm(cpcap, false)' in cpcap

# LP2 source corrections.
assert 'if (WARN_ON(mode != TEGRA_SUSPEND_LP1 && mode != TEGRA_SUSPEND_LP2))' in pm
assert 'ret = cpu_suspend(PHYS_OFFSET - PAGE_OFFSET, tegra_sleep_func);' in pm
assert 'if (ret)\n\t\tpr_err' in pm
assert 'num_online_cpus() != 1' in pm
assert 'flush_cache_all();\n\touter_disable();' in pm
assert 'register_syscore_ops(&tegra_timer_syscore_ops)' in timer
# PMC parser validates only mode-required timing properties and zeroes locals.
assert 'u32 value = 0, values[2] = { 0, 0 };' in pmc
assert 'LP2 keeps the core rail up' in pmc
assert 'core_ok' in pmc and 'vec_ok' in pmc
print('PASS image91 full-tree devices-only DPM gates; display/GPU restoration still blocked')
