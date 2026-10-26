#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from display_power_profile import validate_display_power_artifacts,resolved
from legacy_resources import parse_dtb
p=Path(sys.argv[1]);validate_display_power_artifacts(p)
b=parse_dtb((p/'tegra20-motorola-wingray-android44-displaypm.dtb').read_bytes())
a=parse_dtb((p/'tegra20-motorola-wingray-android44-battery.dtb').read_bytes())
for node,key in [('/spi@7000d600/pmic@0','spi-max-frequency'),('/panel-power','gpio'),('/i2c@7000c000/touchscreen@5b','interrupts')]:
 assert resolved(a,node)[key]==resolved(b,node)[key]
config=(p/'kernel.config').read_text()
for key in ('PM','SUSPEND','CPU_FREQ'):
 assert 'CONFIG_'+key+'=y\n' not in config
script=(ROOT/'diagnostic/display-backlight-cycle.sh').read_text()
assert '--run-backlight-only' in script and 'trap restore EXIT' in script
assert '/sys/power/state' not in script and '/dev/mem' not in script
runtime=(ROOT/'scripts/prepare-android-gpu.py').read_text()
assert 'import /init.xoom-displaypm.rc' in runtime and 'chown system system /sys/class/backlight/lcd-backlight/brightness' in runtime
assert not any('display-backlight-cycle' in (ROOT/'diagnostic'/n).read_text() for n in ('android44-gpu-bootstrap.sh','android44-gpu-report.sh','power-report.sh'))
print('PASS compiled display-power scope, preserved CPCAP/panel/touch, disabled suspend/DVFS, manual cycle guard and Android permissions')
