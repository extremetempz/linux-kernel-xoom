#!/usr/bin/env python3
"""Execute compiled memmap_init_zone with controlled page storage.

Pageblock update is stubbed; the matching FLATMEM build compiles the early
PFN predicates to no-ops. This tests trace placement,
sampling and normal page stores; it cannot diagnose hardware exclusive/cache
behavior or establish that a real allocator mapping is correct.
"""
from pathlib import Path
import argparse,struct,subprocess,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);args=p.parse_args()
syms={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(args.build/'out/vmlinux')],text=True).splitlines():
 parts=line.split()
 if len(parts)==3:syms[parts[2]]=int(parts[0],16)
image=(args.build/'out/arch/arm/boot/Image').read_bytes()
config=(args.build/'out/.config').read_text()
progress_enabled='CONFIG_MOTOROLA_XOOM_BOOT_TRACE_PAGE_PROGRESS=y' in config
detail_enabled='CONFIG_MOTOROLA_XOOM_BOOT_TRACE_PAGE_DETAIL=y' in config
window_enabled='CONFIG_MOTOROLA_XOOM_BOOT_TRACE_PAGE_WINDOW=y' in config
assert progress_enabled and not detail_enabled, 'candidate should use sparse and window progress without per-page detail'
assert window_enabled, 'candidate should enable the bounded page window'
cookie=int(next(x.split('=',1)[1] for x in (args.build/'out/.config').read_text().splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
cases=[('normal',0,8,None,False,0,'valid'),('cross-sample-boundary',2,5,None,False,0,'valid'),('later-block',1024,2,None,False,0,'valid'),('unsampled',4,2,None,False,0,'valid'),('cross-block',1023,3,None,False,0,'valid'),('stop-at-block',0,4,None,True,0,'valid'),('before-window',0x2ebef,2,None,False,0,'valid'),('full-window',0x2ebf0,64,None,False,0,'valid'),('window-end',0x2ec2f,2,None,False,1,'valid'),('not-ready',0,2,None,False,0,'not-ready'),('bad-cookie',0,2,None,False,0,'bad-cookie'),('bad-magic',0,2,None,False,0,'bad-magic')]
for name,start,count,invalid,stop,context,trace_state in cases:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 u.mem_map(0xc0008000,(max(len(image),syms['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
 u.mem_map(0x70000000,0x10000);u.mem_map(0x71000000,0x20000);u.mem_map(0xfe600000,4096)
 # This build's ARM struct page is 32 bytes (the compiled memmap loop scales
 # PFN offsets by five); bias mem_map so the selected high PFNs still land in
 # the small emulated page-storage window.
 mem_map_base=0x71000000-(start<<5)
 assert mem_map_base>0
 u.mem_write(syms['mem_map'],struct.pack('<I',mem_map_base));u.mem_write(syms['wingray_boottrace_static_ready'],b'\x00' if trace_state=='not-ready' else b'\x01')
 packet=bytearray(4096);struct.pack_into('<3I',packet,0,0x584f4f4d,2,cookie)
 if trace_state=='bad-cookie':struct.pack_into('<I',packet,8,cookie^1)
 if trace_state=='bad-magic':struct.pack_into('<I',packet,0,0)
 u.mem_write(0xfe600000,bytes(packet))
 finish=0x7000f000;stack=0x70008000;u.reg_write(UC_ARM_REG_CPSR,0xd3)
 for reg,value in [(UC_ARM_REG_R0,count),(UC_ARM_REG_R1,0),(UC_ARM_REG_R2,0),(UC_ARM_REG_R3,start),(UC_ARM_REG_SP,stack),(UC_ARM_REG_LR,finish)]:u.reg_write(reg,value)
 u.mem_write(stack,struct.pack('<I',context)) # MEMMAP_EARLY or MEMMAP_HOTPLUG
 phases=[];validations=[];block_calls=[];page_writes=[];zone_record={}
 def returned(value):
  ret=u.reg_read(UC_ARM_REG_LR)
  for reg in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R12):u.reg_write(reg,0xdeadbeef)
  u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_CPSR,0xa00000d3);u.reg_write(UC_ARM_REG_PC,ret)
 def code(uc,address,size,opaque):
  if address==syms['pfn_valid']:
   pfn=u.reg_read(UC_ARM_REG_R0);validations.append(pfn);returned(int(pfn!=invalid))
  elif address==syms['set_pfnblock_flags_mask']:
   page=u.reg_read(UC_ARM_REG_R0);kind=u.reg_read(UC_ARM_REG_R1);pfn=u.reg_read(UC_ARM_REG_R2)
   assert 0x71000000<=page<0x71020000 and kind==1 and pfn in range(start,start+count) # MIGRATE_MOVABLE
   block_calls.append(page)
   if stop:u.emu_stop()
   else:returned(0)
 def write(uc,access,address,size,value,opaque):
  if 0x70000000<=address and address+size<=0x70010000:return
  if 0x71000000<=address and address+size<=0x71020000:page_writes.append(address);return
  if address==syms['highest_memmap_pfn']:return
  zone_fields={0xfe600068:'start',0xfe60006c:'end',0xfe600070:'info',0xfe600074:'magic'}
  if address in zone_fields:
   assert size==4
   zone_record[zone_fields[address]]=value
   return
  assert address==0xfe600078 and size==4,(name,hex(address),size,hex(value))
  phases.append(value)
 def invalid(uc,access,address,size,value,opaque):
  print('UNMAPPED',name,hex(uc.reg_read(UC_ARM_REG_PC)),hex(address),size,file=sys.stderr);return False
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_MEM_INVALID,invalid)
 u.emu_start(syms['memmap_init_zone'],finish,count=100000)
 expected=[0x701,0x702] if trace_state=='valid' else []
 for pfn in range(start,start+count):
  sampled=detail_enabled and (pfn & 1023)<4
  def add(step):
   if trace_state=='valid' and progress_enabled and sampled:expected.append(0x80000000|(step<<24)|pfn)
  add(1)
  if pfn==invalid:continue
  add(2);add(3)
  for step in (8,9,10,11,12,13):add(step)
  add(4)
  if pfn%1024==0:
   add(5)
   if stop:break
   add(6)
  if trace_state=='valid' and progress_enabled and pfn & 511 == 511:expected.append(0x90000000|(pfn & 0x0fffffff))
  if trace_state=='valid' and window_enabled and 0x2ebf0<=pfn<=0x2ec2f and pfn & 15==15:expected.append(0xa0000000|(pfn & 0x0fffffff))
 if trace_state=='valid' and not stop:expected.append(0x703)
 assert phases==expected,(name,[hex(v) for v in phases],[hex(v) for v in expected])
 expected_zone={'start':start,'end':start+count,'info':context,'magic':0x574d4150} if trace_state=='valid' else {}
 assert zone_record==expected_zone,(name,zone_record)
 assert validations==[],(name,'FLATMEM predicates expected to compile to no-ops',validations)
 assert len(block_calls)==sum(pfn%1024==0 and pfn!=invalid for pfn in range(start,start+count))
 assert page_writes
 if not stop:assert u.reg_read(UC_ARM_REG_PC)==finish
 print('PASS compiled memmap:',name)
print('Page storage bounds checked; pageblock update is stubbed and no real MMU/allocator behavior is inferred.')
