#!/usr/bin/env python3
"""Execute the actual compiled PID 1 user-fault helper and preservation guards."""
from pathlib import Path
import argparse, struct, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE, UC_PROT_NONE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);a=p.parse_args()
symbols={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(a.build/'out/vmlinux')],text=True).splitlines():
 parts=line.split()
 if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
image=(a.build/'out/arch/arm/boot/Image').read_bytes()
config=(a.build/'out/.config').read_text()
cookie=int(next(x.split('=',1)[1] for x in config.splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
cases=['arm','thumb','negative-code','not-ready','bad-cookie','bad-magic','bad-version','preserve-fatal','preserve-panic','preserve-first']
for case in cases:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
 u.mem_map(0x70000000,0x10000)
 u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0' if case=='not-ready' else b'\1')
 packet=bytearray(4096);struct.pack_into('<3I',packet,0,0 if case=='bad-magic' else 0x584f4f4d,1 if case=='bad-version' else 2,cookie^1 if case=='bad-cookie' else cookie)
 struct.pack_into('<I',packet,0x7c,0xc0123450 if case=='preserve-fatal' else 0xbad00001 if case=='preserve-panic' else 0)
 if case=='preserve-first':struct.pack_into('<I',packet,0x0c,0x55534631)
 if case!='not-ready':u.mem_map(0xfe600000,4096);u.mem_write(0xfe600000,bytes(packet))
 # Any accidental call to freed init code must fail.
 u.mem_protect(symbols['__init_begin'],symbols['__init_end']-symbols['__init_begin'],UC_PROT_NONE)
 values=[0xb6f01234,0xffff0ffc,5,0x60000030 if case=='thumb' else 0x60000010,11,0xffffff80 if case=='negative-code' else 1]
 u.reg_write(UC_ARM_REG_CPSR,0xd3);u.reg_write(UC_ARM_REG_SP,0x70008000)
 for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],values):u.reg_write(reg,value)
 u.mem_write(0x70008000,struct.pack('<2I',*values[4:]))
 finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish)
 writes=[];success=case in ['arm','thumb','negative-code']
 def write(uc,access,address,size,value,opaque):
  if 0x70000000<=address and address+size<=0x70010000:return
  assert success and size==4 and address in range(0xfe60000c,0xfe600028,4)
  writes.append((address,value))
 hook=u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(symbols['wingray_boottrace_record_user_fault'],finish,count=2000)
 assert u.reg_read(UC_ARM_REG_PC)==finish
 if success:
  assert struct.unpack('<7I',u.mem_read(0xfe60000c,28))==(0x55534631,*values)
  assert writes==[(0xfe600010+i*4,v) for i,v in enumerate(values)]+[(0xfe60000c,0x55534631)]
  assert bytes(u.mem_read(0xfe600028,88))==packet[0x28:0x80]
  # The later exit record must preserve this earlier fault detail.
  u.reg_write(UC_ARM_REG_R0,11);u.reg_write(UC_ARM_REG_LR,finish)
  u.hook_del(hook)
  def exit_write(uc,access,address,size,value,opaque):
   if 0x70000000<=address and address+size<=0x70010000:return
   assert size==4 and address in [0xfe600068,0xfe60006c,0xfe600070,0xfe600074,0xfe60007c]
  u.hook_add(UC_HOOK_MEM_WRITE,exit_write)
  u.emu_start(symbols['wingray_boottrace_record_init_exit'],finish,count=2000)
  assert u.reg_read(UC_ARM_REG_PC)==finish
  assert struct.unpack('<7I',u.mem_read(0xfe60000c,28))==(0x55534631,*values)
  assert struct.unpack('<4I',u.mem_read(0xfe600068,16))==(11,0,0,0x58495431)
 else:
  assert not writes
  if case!='not-ready':assert bytes(u.mem_read(0xfe600000,128))==packet[:128]
 print('PASS init user fault:',case)
print('Bounds, signature-last ordering, first-fault/fatal guards and freed-init exclusion checked.')
