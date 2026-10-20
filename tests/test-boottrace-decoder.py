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
struct.pack_into('<II',b,0x78,0x114,0xbad00001)
rc,d=decode(b);assert d['last_phase']['name']=='sparse_init_returned' and d['first_fatal']['kind']=='panic'
struct.pack_into('<I',b,0x7c,0xc0123450)
rc,d=decode(b);assert d['first_fatal']['kind']=='kernel_die_pc'
rc,d=decode(b,1);assert rc==2 and not d['valid'] and 'entry' not in d
rc,d=decode(record(99));assert rc==2 and not d['valid']
rc,d=decode(bytes(16));assert rc!=0 and d is None
for phase,name,zone in [(0x521,'before_node_map_allocation',None),(0x512,'node_map_returned',None),(0x606,'zone_empty_zone_initialized',0),(0x617,'zone_memmap_init_returned',1),(0x651,'unknown',None)]:
 struct.pack_into('<I',b,0x78,phase);rc,d=decode(b)
 assert rc==0 and d['last_phase']['name']==name and d['last_phase'].get('zone_index')==zone
for phase,name,pfn in [(0x701,'memmap_init_zone_entry',None),(0x85000400,'before_pageblock_update','0x400'),(0x89000001,'page_links_set','0x1'),(0x87000001,'unknown',None),(0xb5000400,'unknown',None)]:
 struct.pack_into('<I',b,0x78,phase);rc,d=decode(b)
 assert rc==0 and d['last_phase']['name']==name and d['last_phase'].get('pfn')==pfn
 if pfn is not None:assert d['last_phase']['physical_page']==hex(int(pfn,16)<<12) and 'sampling' in d['last_phase']
for phase,name,pfn in [(0x516,'memmap_init_returned',None),(0x9002ec1f,'memmap_progress_checkpoint','0x2ec1f'),(0xa002ec1f,'memmap_window_checkpoint','0x2ec1f')]:
 struct.pack_into('<I',b,0x78,phase);rc,d=decode(b)
 assert rc==0 and d['last_phase']['name']==name and d['last_phase'].get('pfn')==pfn
 if pfn:assert d['last_phase']['checkpoint'] is True and 'interval_pfns' not in d['last_phase']
 if name=='memmap_window_checkpoint':assert '16-PFN block' in d['last_phase']['sampling']
struct.pack_into('<4I',b,0x68,0x2ebf0,0x2ec30,0x00000100,0x574d4150)
struct.pack_into('<I',b,0x78,0xa002ec1f)
rc,d=decode(b);assert rc==0 and 'mmu_handoff' not in d
assert d['memmap_zone']=={'start_pfn':'0x2ebf0','end_pfn_exclusive':'0x2ec30','size_pfns':64,'nid':0,'zone_index':1,'context':'early','note':d['memmap_zone']['note']}
struct.pack_into('<4I',b,0x68,0x2ebf0,0x2ec30,0xc1000000,0x58012000)
for step,name in [(1,'before_pfn_validation'),(2,'pfn_validation_passed'),(3,'before_single_page_init'),(4,'single_page_init_returned'),(5,'before_pageblock_update'),(6,'pageblock_update_returned')]:
 struct.pack_into('<I',b,0x78,0xb002ec00|(step<<24));rc,d=decode(b)
 assert rc==0 and 'mmu_handoff' not in d and d['last_phase']['name']=='boundary_'+name
 assert d['memmap_zone']['first_page_descriptor']=='0xc1000000' and d['memmap_zone']['page_descriptor_stride']==32
 assert d['memmap_zone']['zone_index']==1 and d['memmap_zone']['nid']==0
 assert d['last_phase']['calculated_descriptor_address']=='0xc1000200'
for phase in [0xb702ec00,0xb502ec01]:
 struct.pack_into('<I',b,0x78,phase);rc,d=decode(b);assert d['last_phase']['name']=='unknown'
struct.pack_into('<I',b,0x78,0x9002edff);rc,d=decode(b)
assert 'calculated_descriptor_address' not in d['last_phase']
print('PASS decoder: old records, extended zone/descriptor records, boundary steps and conservative unknown handling.')
