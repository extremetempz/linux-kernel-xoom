#!/usr/bin/env python3
"""Execute the actual bounded USB link helpers with init memory inaccessible."""
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
cases=[('new','mark',0x10,1,True),('update','mark',0x18,15,True),('success','result',0x10,0,True),('defer','result',0x10,-517,True),('bind-error','result',0x14,-12,True),('invalid-slot','mark',0x28,1,False),('unaligned','mark',0x13,1,False),('invalid-result','result',0x18,-1,False),('not-ready','mark',0x10,1,False),('bad-magic','mark',0x10,1,False),('bad-version','result',0x10,-1,False),('bad-cookie','mark',0x10,1,False),('fatal','mark',0x10,1,False),('panic','result',0x14,0,False),('user-fault','mark',0x1c,1,False),('preserve-error','result',0x14,-12,False),('missing-tag','result',0x10,0,False)]
for name,operation,slot,value,success in cases:
 for cpsr in [0x13,0xd3]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
  u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
  u.mem_map(0x70000000,0x10000);u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0' if name=='not-ready' else b'\1')
  packet=bytearray(4096);struct.pack_into('<3I',packet,0,0 if name=='bad-magic' else 0x584f4f4d,1 if name=='bad-version' else 2,cookie^1 if name=='bad-cookie' else cookie)
  struct.pack_into('<7I',packet,0x0c,0x55534631 if name=='user-fault' else 0xa008d0 if name in ['new','missing-tag'] else 0x554c4e31,7,0x8004000c if name=='preserve-error' else 4,8,0x800,1,2)
  struct.pack_into('<4I',packet,0x68,2,2,2,0x44494131)
  struct.pack_into('<I',packet,0x7c,0xc0123450 if name=='fatal' else 0xbad00001 if name=='panic' else 0)
  if name!='not-ready':u.mem_map(0xfe600000,4096);u.mem_write(0xfe600000,bytes(packet))
  u.mem_protect(symbols['__init_begin'],symbols['__init_end']-symbols['__init_begin'],UC_PROT_NONE)
  u.reg_write(UC_ARM_REG_CPSR,cpsr);u.reg_write(UC_ARM_REG_SP,0x70008000)
  u.reg_write(UC_ARM_REG_R0,slot);u.reg_write(UC_ARM_REG_R1,value&0xffffffff)
  finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);writes=[]
  def write(uc,access,address,size,word,opaque):
   if 0x70000000<=address and address+size<=0x70010000:return
   assert success and size==4 and address in range(0xfe60000c,0xfe600028,4)
   writes.append((address,word))
  u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(symbols['wingray_boottrace_usb_'+operation],finish,count=4000)
  assert u.reg_read(UC_ARM_REG_PC)==finish and u.reg_read(UC_ARM_REG_CPSR)&0xff==cpsr
  if success:
   expected=[]
   if name=='new':expected=[(0xfe600000+off,0) for off in range(0x10,0x28,4)]+[(0xfe60000c,0x554c4e31)]
   word=value if operation=='mark' else 2 if value>=0 else 0x80000000|(struct.unpack_from('<I',packet,slot)[0]<<16)|(-value&0xffff)
   expected.append((0xfe600000+slot,word));assert writes==expected,(name,writes,expected)
   assert bytes(u.mem_read(0xfe600028,88))==packet[0x28:0x80]
  else:
   assert not writes
   if name!='not-ready':assert bytes(u.mem_read(0xfe600000,128))==packet[:128]
 print('PASS USB link helper:',name)
print('34 compiled cases: bounds, first-fault/error preservation, IRQ restoration and freed-init exclusion checked.')
