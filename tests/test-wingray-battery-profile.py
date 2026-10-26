#!/usr/bin/env python3
"""Validate actual compiled DT isolation and exercise rejection of unsafe changes."""
from pathlib import Path
import copy,struct,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from battery_profile import validate_battery_artifacts,validate_trees
from legacy_resources import parse_dtb
p=Path(sys.argv[1]);validate_battery_artifacts(p)
a=parse_dtb((p/'tegra20-motorola-wingray-android44-bluetooth.dtb').read_bytes())
b=parse_dtb((p/'tegra20-motorola-wingray-android44-battery.dtb').read_bytes())
mutations=[('/wingray_battery_monitor','detect-gpios',struct.pack('>3I',struct.unpack('>I',b['/wingray_battery_monitor']['detect-gpios'][:4])[0],151,0)),
 ('/onewire@7000c600','reg',struct.pack('>2I',0x7000d600,0x50)),
 ('/spi@7000d600/pmic@0','spi-max-frequency',struct.pack('>I',1000000)),
 ('/pinmux@70000014/battery-owr-pins/owc','nvidia,pull',struct.pack('>I',0))]
for node,key,value in mutations:
 bad=copy.deepcopy(b);bad[node][key]=value
 try:validate_trees(a,bad)
 except AssertionError:pass
 else:raise AssertionError((node,key,'unsafe change accepted'))
for node in ('/gpio-keys/volume-up','/gpio-keys/volume-down'):
 assert 'wakeup-source' not in b[node]
assert struct.unpack('>I',b['/gpio-keys/volume-up']['linux,code'])[0]==115
assert struct.unpack('>I',b['/gpio-keys/volume-down']['linux,code'])[0]==114
print('PASS compiled battery profile plus negative controls: controller address, charger GPIO, CPCAP frequency, OWR pull; normal volume keys')
