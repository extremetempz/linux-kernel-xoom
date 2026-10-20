#!/usr/bin/env python3
"""Execute the actual init-exit trace helper, including first-fatal guards."""
from pathlib import Path
import argparse, struct, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);args=p.parse_args()
symbols={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(args.build/'out/vmlinux')],text=True).splitlines():
 parts=line.split()
 if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
image=(args.build/'out/arch/arm/boot/Image').read_bytes();config=(args.build/'out/.config').read_text()
cookie=int(next(x.split('=',1)[1] for x in config.splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
for case,status in [('zero',0),('exit-127',0x7f00),('SIGSEGV',11),('SIGILL-core',0x84),('panic-already',2),('not-ready',1),('bad-cookie',1),('bad-magic',1),('bad-version',1),('preserve-fatal',1),('preserve-exit',1)]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
 u.mem_map(0x70000000,0x10000)
 u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0' if case=='not-ready' else b'\1')
 packet=bytearray(4096);struct.pack_into('<3I',packet,0,0 if case=='bad-magic' else 0x584f4f4d,1 if case=='bad-version' else 2,cookie^1 if case=='bad-cookie' else cookie)
 prior=0xc0123450 if case=='preserve-fatal' else 0xbad00001 if case in ['panic-already','preserve-exit'] else 0
 struct.pack_into('<I',packet,0x7c,prior)
 if case=='preserve-exit':struct.pack_into('<4I',packet,0x68,0x7f00,0,0,0x58495431)
 if case!='not-ready':u.mem_map(0xfe600000,4096);u.mem_write(0xfe600000,bytes(packet))
 u.reg_write(UC_ARM_REG_CPSR,0xd3);u.reg_write(UC_ARM_REG_SP,0x70008000)
 finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);u.reg_write(UC_ARM_REG_R0,status)
 writes=[];success=case in ['zero','exit-127','SIGSEGV','SIGILL-core','panic-already']
 def write(uc,access,address,size,value,opaque):
  if 0x70000000<=address and address+size<=0x70010000:return
  assert success and size==4 and address in [0xfe60007c,0xfe600068,0xfe60006c,0xfe600070,0xfe600074]
  writes.append((address,value))
 u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(symbols['wingray_boottrace_record_init_exit'],finish,count=2000)
 assert u.reg_read(UC_ARM_REG_PC)==finish
 if success:
  assert struct.unpack('<4I',u.mem_read(0xfe600068,16))==(status,0,0,0x58495431)
  expected=([(0xfe60007c,0xbad00001)] if not prior else [])+[(0xfe600068,status),(0xfe60006c,0),(0xfe600070,0),(0xfe600074,0x58495431)]
  assert writes==expected
  assert struct.unpack('<I',u.mem_read(0xfe60007c,4))[0]==0xbad00001
 else:
  assert not writes
  if case!='not-ready':assert bytes(u.mem_read(0xfe600000,128))==packet[:128]
 print('PASS init-exit status:',case)
print('Bounds, signature-last ordering, first-fatal and first-exit preservation checked.')
