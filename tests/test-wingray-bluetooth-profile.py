#!/usr/bin/env python3
"""Compare compiled opt-in Bluetooth DT against the hardware-tested base DT."""
from pathlib import Path
import copy,sys
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
from bluetooth_profile import validate_trees,validate_bluetooth_artifacts
from legacy_resources import parse_dtb
p=Path(sys.argv[1]);validate_bluetooth_artifacts(p)
a=parse_dtb((p/'tegra20-motorola-wingray-android44-gpu-fbmap.dtb').read_bytes())
b=parse_dtb((p/'tegra20-motorola-wingray-android44-bluetooth.dtb').read_bytes())
for path,key in [('/wlan-power','gpio'),('/host1x@50000000/dc@54200000','assigned-clock-rates'),('/bluetooth-power','reset-gpios')]:
    c=copy.deepcopy(b);v=bytearray(c[path][key]);v[-1]^=1;c[path][key]=bytes(v)
    try:
        validate_trees(a,c)
    except (AssertionError,KeyError):
        pass
    else:
        raise AssertionError('accepted wrong '+path)
print('PASS compiled Bluetooth DT and configuration; reject changed Wi-Fi power, display clock and reset')
