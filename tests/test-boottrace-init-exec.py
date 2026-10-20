#!/usr/bin/env python3
"""Run actual init-exec wrapper with init memory inaccessible.

External name lookup and exec are controlled returns, not an ELF loader or
userspace test. The old diagnostic is expected to fetch freed init text.
"""
from pathlib import Path
import argparse, struct, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_PROT_NONE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--expect-freed-init-call',action='store_true');args=p.parse_args()
symbols={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(args.build/'out/vmlinux')],text=True).splitlines():
 parts=line.split()
 if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
image=(args.build/'out/arch/arm/boot/Image').read_bytes()
config=(args.build/'out/.config').read_text()
cookie=int(next(x.split('=',1)[1] for x in config.splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
cases=[('success',0),('ENOENT',-2),('ENOEXEC',-8),('EACCES',-13),('not-ready',0),('wrong-cookie',-2),('wrong-version',-2),('wrong-magic',-2)]
if args.expect_freed_init_call:cases=cases[:1]
for case,result in cases:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
 begin,end=symbols['__init_begin'],symbols['__init_end'];assert begin%4096==end%4096==0
 u.mem_protect(begin,end-begin,UC_PROT_NONE)
 u.mem_map(0x70000000,0x10000);u.mem_map(0x71000000,4096)
 filename=0x71000000;name=0x71000100;u.mem_write(filename,b'/init\0')
 u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0' if case=='not-ready' else b'\1')
 if case!='not-ready':
  u.mem_map(0xfe600000,4096);packet=bytearray(4096)
  struct.pack_into('<3I',packet,0,0 if case=='wrong-magic' else 0x584f4f4d,1 if case=='wrong-version' else 2,cookie^1 if case=='wrong-cookie' else cookie)
  u.mem_write(0xfe600000,bytes(packet))
 u.reg_write(UC_ARM_REG_CPSR,0xd3);u.reg_write(UC_ARM_REG_SP,0x70008000)
 finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);u.reg_write(UC_ARM_REG_R0,filename)
 writes=[];calls=[]
 def returned(value):
  ret=u.reg_read(UC_ARM_REG_LR)
  for reg in [UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R12]:u.reg_write(reg,0xdeadbeef)
  u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_CPSR,0xa00000d3);u.reg_write(UC_ARM_REG_PC,ret)
 def code(uc,address,size,opaque):
  if address==symbols['getname_kernel']:
   assert u.reg_read(UC_ARM_REG_R0)==filename;calls.append('name');returned(name)
  elif address==symbols['do_execve']:
   assert u.reg_read(UC_ARM_REG_R0)==name
   assert struct.unpack('<I',u.mem_read(u.reg_read(UC_ARM_REG_R1),4))[0]==filename
   calls.append('exec');returned(result)
 def write(uc,access,address,size,value,opaque):
  if 0x70000000<=address and address+size<=0x70010000:return
  if address==symbols['argv_init'] and size==4 and value==filename:return
  assert case in ['success','ENOENT','ENOEXEC','EACCES'] and size==4 and address==0xfe600078
  writes.append(value)
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 try:u.emu_start(symbols['run_init_process'],finish,count=5000)
 except UcError:
  if not args.expect_freed_init_call:raise
  assert u.reg_read(UC_ARM_REG_PC)==symbols['of_get_flat_dt_root'] and not calls
  print('REPRODUCED build 15 fetch from freed init helper at',hex(symbols['of_get_flat_dt_root']))
  continue
 assert not args.expect_freed_init_call,'Old diagnostic did not reproduce the expected fault'
 assert u.reg_read(UC_ARM_REG_PC)==finish and u.reg_read(UC_ARM_REG_R0)==result&0xffffffff
 assert calls==['name','exec']
 expected=[0x420,0x421 if result==0 else 0xc1000000|(-result&0xffff)]
 assert writes==(expected if case in ['success','ENOENT','ENOEXEC','EACCES'] else [])
 print('PASS post-init exec trace:',case)
print('Init section is inaccessible throughout; only external exec/name operations are stubbed.')
