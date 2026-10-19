#!/usr/bin/env python3
"""Execute the compiled static-map callback with stubbed kernel services.

Checks the mapping request/guard and trace write; does not emulate iotable_init
page-table construction or actual hardware translation/cache behavior.
"""
from pathlib import Path
import argparse, struct, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);args=p.parse_args()
symbols={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(args.build/'out/vmlinux')],text=True).splitlines():
 parts=line.split()
 if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
image=(args.build/'out/arch/arm/boot/Image').read_bytes()
cookie=int(next(x.split('=',1)[1] for x in (args.build/'out/.config').read_text().splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
for wingray in (True,False):
 for matching_cookie in (True,False):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
  u.mem_map(0xc0008000,(len(image)+4095)//4096*4096);u.mem_write(0xc0008000,image)
  u.mem_map(0x70000000,0x10000);u.reg_write(UC_ARM_REG_SP,0x70008000)
  finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);u.reg_write(UC_ARM_REG_CPSR,0xd3)
  state={'base_calls':0,'trace_calls':0,'writes':[]}
  def returned(value):
   ret=u.reg_read(UC_ARM_REG_LR)
   for reg in [UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R12]:u.reg_write(reg,0xdeadbeef)
   u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_CPSR,0xa00000d3);u.reg_write(UC_ARM_REG_PC,ret)
  def text(address):
   b=bytearray()
   for i in range(64):
    v=bytes(u.mem_read(address+i,1))
    if v==b'\0':return b.decode()
    b.extend(v)
   raise AssertionError('Unterminated compatible')
  def code(uc,address,size,opaque):
   if address==symbols['iotable_init']:
    pointer=u.reg_read(UC_ARM_REG_R0);count=u.reg_read(UC_ARM_REG_R1)
    if count==4:
     state['base_calls']+=1
     ranges=[]
     for i in range(4):
      va,pfn,length,typ=struct.unpack('<4I',u.mem_read(pointer+16*i,16));ranges.append((va,va+length))
     assert all(end<=0xfe600000 or begin>=0xfe601000 for begin,end in ranges)
    else:
     assert wingray and count==1
     assert struct.unpack('<4I',u.mem_read(pointer,16))==(0xfe600000,0x1fe00,4096,0)
     state['trace_calls']+=1;u.mem_map(0xfe600000,4096)
     packet=bytearray(4096);struct.pack_into('<3I',packet,0,0x584f4f4d,2,cookie if matching_cookie else cookie^1)
     u.mem_write(0xfe600000,bytes(packet))
    returned(0)
   elif address==symbols['of_get_flat_dt_root']:returned(0x10)
   elif address==symbols['of_flat_dt_is_compatible']:
    assert u.reg_read(UC_ARM_REG_R0)==0x10 and text(u.reg_read(UC_ARM_REG_R1))=='motorola,wingray'
    returned(int(wingray))
  def write(uc,access,address,size,value,opaque):
   if 0x70000000<=address and address+size<=0x70010000:return
   assert wingray and matching_cookie and address==0xfe600078 and size==4 and value==0x103
   state['writes'].append(address)
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(symbols['tegra_map_common_io'],finish,count=2000)
  assert u.reg_read(UC_ARM_REG_PC)==finish
  assert state['base_calls']==1 and state['trace_calls']==int(wingray)
  assert len(state['writes'])==int(wingray and matching_cookie)
print('PASS: 4 compiled map_io cases; one-page descriptor, IO-map non-overlap, Wingray guard and cookie guard checked.')
board=(args.build/'source/arch/arm/mach-tegra/board-wingray.c').read_text()
trace=board.split('#ifdef CONFIG_MOTOROLA_XOOM_BOOT_TRACE',1)[1]
assert 'ioremap_nocache(' not in trace and 'iounmap(' not in trace
print('PASS: early board trace helper has no dynamic ioremap/iounmap call.')
