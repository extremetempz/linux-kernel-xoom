#!/usr/bin/env python3
"""Compile actual suspend entry with controls; verify the isolated config."""
import argparse
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT/'sources/kernel-donor'

def function(source, name):
    start = source.index(name + '(')
    start = source.rfind('\n', 0, start) + 1
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

def validate_config(path):
    enabled = {line.split('=', 1)[0][7:] for line in path.read_text().splitlines()
               if line.startswith('CONFIG_') and line.endswith('=y')}
    for option in ('MOTOROLA_WINGRAY_PM_PREPARE','PM','PM_SLEEP','SUSPEND',
                   'PM_DEBUG','PM_SLEEP_DEBUG','PM_SLEEP_SMP','HOTPLUG_CPU',
                   'SMP','CACHE_L2X0','MFD_CPCAP_WINGRAY_IRQ_TEST','PSTORE_RAM',
                   'PSTORE_CONSOLE','FB_TEGRA_WINGRAY_DISPLAY_PM'):
        assert option in enabled, option
    for option in ('PM_AUTOSLEEP','PM_WAKELOCKS','PM_TEST_SUSPEND','HIBERNATION',
                   'DPM_WATCHDOG','CPU_FREQ','CPU_IDLE','REGULATOR_CPCAP',
                   'FB_TEGRA_WINGRAY_DC_RESUME_TEST','FB_TEGRA_WINGRAY_DC_TRACE_TEST'):
        assert option not in enabled, option
    assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="tegra20-motorola-wingray-android44-wakeirqecc"' in path.read_text()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--config', type=Path)
a = p.parse_args()
suspend = (KERNEL/'kernel/power/suspend.c').read_text()
helper = function((KERNEL/'include/linux/wingray_pm_prepare.h').read_text(), 'wingray_pm_prepare_only')
actual = function(suspend, 'pm_suspend')
lower = function(suspend, 'suspend_devices_and_enter')
assert lower.index('wingray_pm_prepare_only()') < lower.index('platform_suspend_begin(state)')
assert lower.index('return -EOPNOTSUPP;') < lower.index('dpm_suspend_start(')
pm_init = function((KERNEL/'arch/arm/mach-tegra/pm.c').read_text(), 'tegra_init_suspend')
assert pm_init.index('wingray_pm_prepare_only()') < pm_init.index('tegra_tear_down_cpu_init()') < pm_init.index('suspend_set_ops(')
source = r'''
#include <stdbool.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
typedef int suspend_state_t;
#define PM_SUSPEND_ON 0
#define PM_SUSPEND_MAX 4
static bool config, wingray;
#define CONFIG_MOTOROLA_WINGRAY_PM_PREPARE config
#define IS_ENABLED(x) (x)
static bool of_machine_is_compatible(const char *s) { assert(!strcmp(s,"motorola,wingray")); return wingray; }
static int calls, markers;
static struct {int success, fail;} suspend_stats;
static int enter_state(int state,bool freezer_only) {assert(!freezer_only);calls++; return state == 3 ? -EIO : 0;}
static void pm_suspend_marker(const char *s) {(void)s; markers++;}
static void dpm_save_failed_errno(int error) {assert(error == -EIO);}
'''+helper+'\n'+actual+r'''
int main(void) {
 config = wingray = true;
 for (int state=1; state<PM_SUSPEND_MAX; state++) assert(pm_suspend(state)==-EOPNOTSUPP);
 assert(!calls && !markers && !suspend_stats.success && !suspend_stats.fail);
 assert(pm_suspend(0)==-EINVAL && pm_suspend(4)==-EINVAL);
 wingray=false; assert(pm_suspend(1)==0); assert(calls==1 && markers==2);
 wingray=true; config=false; assert(pm_suspend(2)==0); assert(pm_suspend(3)==-EIO);
 assert(calls==3 && markers==6 && suspend_stats.success==2 && suspend_stats.fail==1);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp)/'test.c'; exe = Path(tmp)/'test'
    c.write_text(source)
    subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
if a.config:
    validate_config(a.config)
    # Demonstrate that removing the mandatory gate cannot pass validation.
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp)/'bad.config'
        bad.write_text(a.config.read_text().replace('CONFIG_MOTOROLA_WINGRAY_PM_PREPARE=y',''))
        try: validate_config(bad)
        except AssertionError: pass
        else: raise AssertionError('Missing entry block accepted')
print('PASS actual system-sleep gate, normal-board controls and preparation scope; hardware sleep untested')
