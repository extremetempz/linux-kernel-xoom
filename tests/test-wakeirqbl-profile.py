#!/usr/bin/env python3
"""Validate the IRQ-only + backlight-only profile and forbid DC/PM drift."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from wakeirq_profile import validate_wakeirq_artifacts
p=Path(sys.argv[1])
validate_wakeirq_artifacts(p, require_dc=False)
cfg=(p/'kernel.config').read_text()
for name in ('MFD_CPCAP_WINGRAY_IRQ_TEST','FB_TEGRA_WINGRAY_DISPLAY_PM','MFD_CPCAP','SMP','CACHE_L2X0'):
    assert 'CONFIG_'+name+'=y\n' in cfg,name
for name in ('FB_TEGRA_WINGRAY_DC_RESUME_TEST','PM','PM_SLEEP','SUSPEND','CPU_FREQ','REGULATOR_CPCAP'):
    assert 'CONFIG_'+name+'=y\n' not in cfg,name
assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="tegra20-motorola-wingray-android44-wakeirq"\n' in cfg
assert (p/'tegra20-motorola-wingray-android44-wakeirq.dtb').is_file()
print('PASS IRQ-only backlight-only profile: LIC/ON test same, DC/PM/SUSPEND off; wake hardware unverified')
