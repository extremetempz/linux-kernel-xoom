#!/usr/bin/env python3
"""Run the actual bounded GPIO trace helper with init memory inaccessible."""
from pathlib import Path
import argparse,struct,subprocess,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_PROT_NONE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);a=p.parse_args()
symbols={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(a.build/'out/vmlinux')],text=True).splitlines():
 f=line.split()
 if len(f)==3:symbols[f[2]]=int(f[0],16)
image=(a.build/'out/arch/arm/boot/Image').read_bytes();config=(a.build/'out/.config').read_text()
cookie=int(next(x.split('=',1)[1] for x in config.splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
cases=[('all-clear',0,True),('all-set',255,True),('mask-high-bits',0xffffffff,True),('mixed',0x59,True),('user-fault',0xff,True),('not-ready',0xff,False),('bad-magic',0xff,False),('bad-version',0xff,False),('bad-cookie',0xff,False),('fatal',0xff,False),('panic',0xff,False)]
for name,state,success in cases:
 for cpsr in [0x13,0xd3]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
  u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
  u.mem_map(0x70000000,0x10000);u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0' if name=='not-ready' else b'\1')
  packet=bytearray(range(128))+bytearray(4096-128)
  struct.pack_into('<3I',packet,0,0 if name=='bad-magic' else 0x584f4f4d,1 if name=='bad-version' else 2,cookie^1 if name=='bad-cookie' else cookie)
  struct.pack_into('<I',packet,0x0c,0x55534631 if name=='user-fault' else 0x554c4e31)
  struct.pack_into('<I',packet,0x7c,0xc0123450 if name=='fatal' else 0xbad00001 if name=='panic' else 0)
  if name!='not-ready':u.mem_map(0xfe600000,4096);u.mem_write(0xfe600000,bytes(packet))
  u.mem_protect(symbols['__init_begin'],symbols['__init_end']-symbols['__init_begin'],UC_PROT_NONE)
  u.reg_write(UC_ARM_REG_CPSR,cpsr);u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_R0,state)
  finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);writes=[]
  def write(uc,access,address,size,word,opaque):
   if 0x70000000<=address and address+size<=0x70010000:return
   assert success and size==4 and address in [0xfe600048,0xfe60004c]
   writes.append((address,word))
  u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(symbols['wingray_boottrace_gpio_state'],finish,count=4000)
  assert u.reg_read(UC_ARM_REG_PC)==finish and u.reg_read(UC_ARM_REG_CPSR)&0xff==cpsr
  if success:
   assert writes==[(0xfe60004c,state&255),(0xfe600048,0x47504931)]
   expected=bytearray(packet);struct.pack_into('<II',expected,0x48,0x47504931,state&255)
   assert bytes(u.mem_read(0xfe600000,128))==expected[:128]
  else:
   assert not writes
   if name!='not-ready':assert bytes(u.mem_read(0xfe600000,128))==packet[:128]
 print('PASS GPIO trace:',name)
print('22 compiled cases: bounded writes, header/fatal guards, IRQ restoration, USB/user-fault preservation and freed-init exclusion.')
