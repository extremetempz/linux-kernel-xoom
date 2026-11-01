#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base='XOOM_FRESH_REPORT_V2 abc\nXOOM_UPTIME_START 100.00 90.00\nXOOM_BATTERY_MONITOR_V1_BEGIN\nSUPPLY ac\nPROPERTY online\n1\nSUPPLY battery\nPROPERTY capacity\n80\nPROPERTY voltage_now\n4000000\nPROPERTY current_now\n-123000\nPROPERTY status\nDischarging\nXOOM_BATTERY_MONITOR_V1_END\n'
after=base.replace('100.00','700.00').replace('PROPERTY capacity\n80','PROPERTY capacity\n73')
with tempfile.TemporaryDirectory() as t:
 t=Path(t); (t/'b').write_text(base); (t/'a').write_text(after)
 r=subprocess.run([str(ROOT/'scripts/power-compare.py'),'--before',str(t/'b'),'--after',str(t/'a'),'--label','x','--output',str(t/'o.json')],check=True,capture_output=True,text=True)
 o=json.loads((t/'o.json').read_text()); assert o['seconds']==600 and o['capacity_delta']==-7 and o['label']=='x'
 print('PASS power report parse and interval/capacity comparison')
