#!/usr/bin/env python3
"""Execute compiled mapping/virtual-store snippets and converter call flow.

Unicorn supplies mappings. Descriptor checks are software checks, not a model
of the Tegra MMU, memory controller or cache/reset retention.
"""
from pathlib import Path
import argparse, struct, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE, UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);args=p.parse_args()
def symbols(path):
 result={}
 for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(path)],text=True).splitlines():
  parts=line.split()
  if len(parts)==3:result[parts[2]]=int(parts[0],16)
 return result
ks=symbols(args.build/'out/vmlinux');zs=symbols(args.build/'out/arch/arm/boot/compressed/vmlinux')
k=(args.build/'out/arch/arm/boot/Image').read_bytes();z=(args.build/'out/arch/arm/boot/zImage').read_bytes()
regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12,UC_ARM_REG_SP,UC_ARM_REG_LR]
def machine(blob,load):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 low=load&~4095;u.mem_map(low,(load-low+len(blob)+4095)//4096*4096);u.mem_write(load,blob)
 return u
for flags in range(16):
 u=machine(k,0x8000);u.mem_map(0x4000,0x4000);u.mem_write(0x4000,b'\xa5'*0x4000)
 initial=[0x12340000+i*0x100 for i in range(15)];initial[4]=0x4000
 for reg,val in zip(regs,initial):u.reg_write(reg,val)
 cpsr=0xd3|(flags<<28);u.reg_write(UC_ARM_REG_CPSR,cpsr);writes=[]
 def mapping_write(uc,access,address,size,value,opaque):
  assert address==0x4000+0x37f8 and size==4
  writes.append(value)
 u.hook_add(UC_HOOK_MEM_WRITE,mapping_write)
 start=ks['wingray_trace_map_begin']-0xc0000000;end=ks['wingray_trace_map_end']-0xc0000000
 u.emu_start(start,end,count=100)
 assert u.reg_read(UC_ARM_REG_PC)==end and writes==[0x1fe00452]
 desc=writes[0]
 assert desc&0xfff00000==0x1fe00000 and desc&3==2 # section base/type
 assert desc&0x10 and (desc>>10)&3==1 and (desc>>15)&1==0 # XN; privileged RW only
 assert (desc>>5)&15==2 and desc&((7<<12)|(3<<2))==0 # IO domain; strongly ordered
 pg=bytes(u.mem_read(0x4000,0x4000));assert pg[:0x37f8]==b'\xa5'*0x37f8 and pg[0x37fc:]==b'\xa5'*(0x4000-0x37fc)
 assert u.reg_read(UC_ARM_REG_CPSR)==cpsr
 for i,reg in enumerate(regs):
  if i not in (0,3):assert u.reg_read(reg)==initial[i]
for name,off,value in [('switched',0x50,9),('bss',0x54,10)]:
 for flags in range(16):
  u=machine(k,0xc0008000);u.mem_map(0xdfe00000,4096);u.mem_write(0xdfe00000,b'\xa5'*4096)
  initial=[0x12340000+i*0x100 for i in range(15)]
  for reg,val in zip(regs,initial):u.reg_write(reg,val)
  cpsr=0xd3|(flags<<28);u.reg_write(UC_ARM_REG_CPSR,cpsr);writes=[]
  def mark_write(uc,access,address,size,val,opaque):
   assert address==0xdfe00000+off and size==4 and val==value;writes.append(address)
  u.hook_add(UC_HOOK_MEM_WRITE,mark_write)
  u.emu_start(ks['wingray_trace_'+name+'_begin'],ks['wingray_trace_'+name+'_end'],count=100)
  assert len(writes)==1 and u.reg_read(UC_ARM_REG_CPSR)==cpsr
  for i,reg in enumerate(regs):
   if i not in (3,12):assert u.reg_read(reg)==initial[i]
print('PASS: 48 compiled mapping/post-MMU snippets; descriptor, write bounds, boot registers and flags checked.')
for returns in [(0,),(-22,),(1,0),(1,-22),(1,1)]:
 u=machine(z,0x00a00800);u.mem_map(0x1fe00000,4096);u.mem_map(0x20000000,0x10000)
 values={UC_ARM_REG_SP:0x20008000,UC_ARM_REG_R0:0x321,UC_ARM_REG_R1:0x456,UC_ARM_REG_R2:0x789,UC_ARM_REG_R3:0xabc,UC_ARM_REG_R4:0x8001,UC_ARM_REG_R5:32768,UC_ARM_REG_R6:0xafbfe0,UC_ARM_REG_R8:0x100,UC_ARM_REG_R12:0xdef,UC_ARM_REG_LR:0x123}
 for reg,val in values.items():u.reg_write(reg,val)
 u.reg_write(UC_ARM_REG_CPSR,0xd3);calls=[]
 def call(uc,address,size,opaque):
  if address==0xa00800+zs['atags_to_fdt']:
   index=len(calls);assert index<len(returns)
   assert uc.reg_read(UC_ARM_REG_R0)==0x100
   assert uc.reg_read(UC_ARM_REG_R1)==0xafbfe0 and uc.reg_read(UC_ARM_REG_R2)==32768
   calls.append(index);uc.reg_write(UC_ARM_REG_R0,returns[index]&0xffffffff)
   uc.reg_write(UC_ARM_REG_CPSR,0xa00000d3) # C return flags are unspecified
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,address,size,value,opaque):
  assert (0x1fe00000<=address and address+size<=0x1fe00080) or (0x20000000<=address and address+size<=0x20010000)
 u.hook_add(UC_HOOK_CODE,call);u.hook_add(UC_HOOK_MEM_WRITE,write)
 end=0xa00800+zs['wingray_trace_atag_end']
 u.emu_start(0xa00800+zs['wingray_trace_convert_begin'],end,count=1000)
 assert u.reg_read(UC_ARM_REG_PC)==end and len(calls)==len(returns)
 assert struct.unpack('<i',u.mem_read(0x1fe0002c,4))[0]==returns[-1]
 assert struct.unpack('<I',u.mem_read(0x1fe00034,4))[0]==2
print('PASS: 5 compiled converter caller scenarios, including no retry and retry errors; actual status preserved.')
cookie=int(next(x.split('=',1)[1] for x in (args.build/'out/.config').read_text().splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
for matching in (True,False):
 u=machine(k,0xc0008000);u.mem_map(0xdfe00000,4096);u.mem_map(0x70000000,0x10000)
 packet=bytearray(128);struct.pack_into('<3I',packet,0,0x584f4f4d,2,cookie if matching else cookie^1);u.mem_write(0xdfe00000,bytes(packet))
 u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_CPSR,0xd3)
 state={'stopped_at_call':False,'marks':0}
 def code(uc,address,size,opaque):
  insn=struct.unpack('<I',uc.mem_read(address,4))[0]
  if insn&0x0f000000==0x0b000000:
   state['stopped_at_call']=True;uc.emu_stop()
 def write(uc,access,address,size,value,opaque):
  if 0x70000000<=address and address+size<=0x70010000:return
  assert address==0xdfe00058 and size==4 and value==11
  state['marks']+=1
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(ks['start_kernel'],0,count=500)
 assert state['stopped_at_call'] and state['marks']==int(matching)
 assert struct.unpack('<I',u.mem_read(0xdfe00058,4))[0]==(11 if matching else 0)
print('PASS: 2 compiled start_kernel prologues; C marker precedes external calls and rejects a wrong cookie.')
