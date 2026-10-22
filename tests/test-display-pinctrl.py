#!/usr/bin/env python3
"""Cross-check LCD DT settings against the pinned driver's actual capabilities.

The known-failed image28 DT must be rejected; shared pulls must correspond to
the original Motorola board's shared register locations and captured values.
"""
from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parents[1];tree=root/'sources/kernel-donor'
driver=(tree/'drivers/pinctrl/pinctrl-tegra20.c').read_text()
legacy=(root/'sources/kernel-baseline/arch/arm/mach-tegra/pinmux-t2-tables.c').read_text()
caps={}
for args in re.findall(r'\b(MUX_PG|PULL_PG)\(([^\n]+)\)',driver):
 kind,values=args;v=[x.strip() for x in values.split(',')]
 if kind=='MUX_PG' and len(v)==11 and v[5].startswith(('0x','-')):
  caps[v[0]]={'functions':v[1:5],'tri':int(v[5],0)>=0,'pull':int(v[9],0)>=0,'reg':(int(v[9],0),int(v[10],0))}
 elif kind=='PULL_PG' and len(v)==3 and v[1].startswith('0x'):
  caps[v[0]]={'functions':[],'tri':False,'pull':True,'reg':(int(v[1],0),int(v[2],0))}
def check(dts):
 seen={};count=0
 for block in re.findall(r'\{([^{}]+)\}',dts):
  match=re.search(r'nvidia,pins\s*=([^;]+);',block)
  if not match:continue
  groups=re.findall(r'"([^"]+)"',match[1])
  func=re.search(r'nvidia,function\s*=\s*"([^"]+)"',block)
  pull=re.search(r'nvidia,pull\s*=\s*<(\d+)>',block)
  tri='nvidia,tristate' in block
  for group in groups:
   cap=caps[group]
   if func:
    assert func[1].upper() in cap['functions'],group+' invalid mux'
    if func[1]=='displaya':count+=1
   if tri:assert cap['tri'],group+' unsupported tristate'
   if pull:
    assert cap['pull'],group+' unsupported pull'
    seen[group]=int(pull[1])
 assert count==31
 expected={'ld17_0':1,'ld19_18':1,'ld21_20':1,'ld23_22':1,'lc':2,'ls':2}
 assert seen==expected
 # Legacy per-signal descriptors map to the same six shared register fields.
 for line in legacy.splitlines():
  m=re.search(r'PINGROUP\(([^,]+),(.+)\),',line)
  if not m:continue
  name=m[1].strip().lower()
  if name not in caps or 'DISPLAYA' not in caps[name]['functions']:continue
  fields=[x.strip() for x in (m[1]+','+m[2]).split(',')]
  if len(fields)!=13:continue
  reg=(int(fields[-2],0),int(fields[-1],0))
  assert reg in [caps[g]['reg'] for g in expected],name+' legacy pull mismatch'
 return True
current=(tree/'arch/arm/boot/dts/tegra20-motorola-wingray-display.dts').read_text()
assert check(current)
old=subprocess.check_output(['git','-C',str(tree),'show','16b70590:arch/arm/boot/dts/tegra20-motorola-wingray-display.dts'],text=True)
try:check(old)
except AssertionError as e:assert 'unsupported pull' in str(e)
else:raise AssertionError('Failed image28 pull settings were not rejected')
print('PASS 31 muxes and six shared pulls match actual Tegra20 capabilities; image28 regression rejected.')
