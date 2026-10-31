#!/usr/bin/env python3
"""Source gates for the LP2 return/cache/timer/PMC corrections; no hardware."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
K = ROOT / 'sources/kernel-donor'
pm = (K/'arch/arm/mach-tegra/pm.c').read_text()
timer = (K/'drivers/clocksource/tegra20_timer.c').read_text()
pmc = (K/'drivers/soc/tegra/pmc.c').read_text()
assert 'mode != TEGRA_SUSPEND_LP1 && mode != TEGRA_SUSPEND_LP2' in pm
assert 'ret = cpu_suspend(PHYS_OFFSET - PAGE_OFFSET, tegra_sleep_func);' in pm
assert 'if (ret)\n\t\tpr_err' in pm
assert 'num_online_cpus() != 1' in pm
assert pm.index('flush_cache_all();') < pm.index('outer_disable();') < pm.index('tegra_sleep_cpu_finish(v2p);')
assert 'register_syscore_ops(&tegra_timer_syscore_ops)' in timer
assert 'tegra_timer_syscore_suspend' in timer
assert 'u32 value = 0, values[2] = { 0, 0 };' in pmc
assert 'pmc->suspend_mode = TEGRA_SUSPEND_NONE;' in pmc
assert 'core_ok' in pmc and 'vec_ok' in pmc
assert 'if (pmc->suspend_mode >= TEGRA_SUSPEND_LP1)' in pmc
print('PASS LP2 return propagation, one-CPU/cache ordering, timer syscore and mode-specific PMC parser; hardware unverified')
