#!/usr/bin/env python3
"""Execute the compiled bounded panic-message helper; no fatal handler/MMU emulation."""
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
image=(args.build/'out/arch/arm/boot/Image').read_bytes()
config=(args.build/'out/.config').read_text()
cookie=int(next(x.split('=',1)[1] for x in config.splitlines() if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
for case in ['long','short','empty','not-ready','wrong-magic','wrong-version','wrong-cookie','no-fatal','other-fatal','preserve-message','preserve-init-exit']:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
 u.mem_map(0x70000000,0x10000);u.mem_map(0x71000000,4096)
 message=b'No working i' if case=='long' else b'x\0' if case=='short' else b'\0'
 pointer=0x71001000-len(message);u.mem_write(pointer,message)
 u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0' if case=='not-ready' else b'\1')
 packet=bytearray(4096)
 struct.pack_into('<3I',packet,0,0 if case=='wrong-magic' else 0x584f4f4d,1 if case=='wrong-version' else 2,cookie^1 if case=='wrong-cookie' else cookie)
 fault=0 if case=='no-fatal' else 0xc0123450 if case=='other-fatal' else 0xbad00001
 struct.pack_into('<I',packet,0x7c,fault)
 if case=='preserve-init-exit':struct.pack_into('<4I',packet,0x68,0x7f00,0,0,0x58495431)
 if case=='preserve-message':
  packet[0x68:0x74]=b'first reason';struct.pack_into('<I',packet,0x74,0x504e4331)
 if case!='not-ready':u.mem_map(0xfe600000,4096);u.mem_write(0xfe600000,bytes(packet))
 u.reg_write(UC_ARM_REG_CPSR,0xd3);u.reg_write(UC_ARM_REG_SP,0x70008000)
 finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);u.reg_write(UC_ARM_REG_R0,pointer)
 writes=[]
 def write(uc,access,address,size,value,opaque):
  if 0x70000000<=address and address+size<=0x70010000:return
  assert case in ['long','short','empty'] and size==4 and address in range(0xfe600068,0xfe600078,4)
  writes.append((address,value))
 u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(symbols['wingray_trace_panic_message'],finish,count=2000)
 assert u.reg_read(UC_ARM_REG_PC)==finish
 if case in ['long','short','empty']:
  expected=message[:12].split(b'\0',1)[0].ljust(12,b'\0')
  assert bytes(u.mem_read(0xfe600068,12))==expected
  assert [a for a,v in writes]==list(range(0xfe600068,0xfe600078,4))
  assert writes[-1][1]==0x504e4331
  assert bytes(u.mem_read(0xfe600000,0x68))==packet[:0x68]
  assert bytes(u.mem_read(0xfe600078,8))==packet[0x78:0x80]
 else:
  assert not writes
  if case!='not-ready':assert bytes(u.mem_read(0xfe600000,128))==packet[:128]
 print('PASS panic prefix:',case)
print('Bounded loads, guards, four-word publication and first-message preservation checked.')
