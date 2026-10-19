#!/usr/bin/env python3
"""Offline trace-format regression checks, including the old false status."""
from pathlib import Path
import json, struct, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
def decode(data,cookie=0x584d0003):
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'record';path.write_bytes(data)
  r=subprocess.run(['python3',str(root/'scripts/decode-boottrace.py'),str(path),'--expected-cookie',hex(cookie)],capture_output=True,text=True)
  return r.returncode,json.loads(r.stdout) if r.stdout else None
def record(version=2,cookie=0x584d0003):
 b=bytearray(128);struct.pack_into('<3I',b,0,0x584f4f4d,version,cookie);return b
b=record(1);struct.pack_into('<I',b,0x2c,256);struct.pack_into('<I',b,0x34,2)
rc,d=decode(b);assert rc==0 and d['atag_return_code'] is None and d['raw_atag_status_word']=='0x100' and 'atag_status_warning' in d
assert d['entry']['sctlr_after_mode_setup'] is None
b=record();struct.pack_into('<i',b,0x2c,-22);struct.pack_into('<I',b,0x34,2);struct.pack_into('<I',b,0x50,9)
rc,d=decode(b);assert rc==0 and d['atag_return_code']==-22 and d['stages']['mmu_switched_entry']
assert not d['stages']['bss_cleared'] and 'mmu_handoff' not in d
struct.pack_into('<I',b,0x44,6);struct.pack_into('<4I',b,0x68,0xc50079,0xafbfe0,0x4000,0xc01be2e0)
rc,d=decode(b);assert rc==0 and d['mmu_handoff']['ttbr']=='0x4000'
struct.pack_into('<I',b,0x78,0x201)
rc,d=decode(b);assert d['last_phase']['name']=='paging_init_returned'
struct.pack_into('<I',b,0x78,0xdead)
rc,d=decode(b);assert d['last_phase']['name']=='unknown'
rc,d=decode(b,1);assert rc==2 and not d['valid'] and 'entry' not in d
rc,d=decode(record(99));assert rc==2 and not d['valid']
rc,d=decode(bytes(16));assert rc!=0 and d is None
print('PASS: 8 offline decoder cases; old status is not misreported and phase names decode safely.')
