#!/usr/bin/env python3
"""Run the compiled Tegra UDC probe with controlled external dependencies."""
from pathlib import Path
import argparse,struct,subprocess,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);a=p.parse_args()
symbols={}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'),'-n',str(a.build/'out/vmlinux')],text=True).splitlines():
 f=line.split()
 if len(f)==3:symbols[f[2]]=int(f[0],16)
image=(a.build/'out/arch/arm/boot/Image').read_bytes()
for case,expected in [('success',0),('resume-fails',-110),('child-fails',-12),('prepare-fails',-5),('enable-fails',-5),('phy-defer',-517),('no-memory',-12),('no-match',-22)]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
 u.mem_map(0xc0008000,(max(len(image),symbols['_end']-0xc0008000)+4095)//4096*4096);u.mem_write(0xc0008000,image)
 u.mem_write(symbols['wingray_boottrace_static_ready'],b'\0')
 u.mem_map(0x70000000,0x10000);u.mem_map(0x71000000,0x10000)
 udc,phy,soc,pdev,clk,child=[0x71000000+i*4096 for i in range(6)]
 callback=0x7000e000
 # ARM32 usb_phy fixture: set_suspend is at offset 0x44 in this ABI.
 u.mem_write(phy+0x44,struct.pack('<I',callback))
 calls=[];resumes=[]
 returns={'devm_kmalloc':0 if case=='no-memory' else udc,'of_device_get_match_data':0 if case=='no-match' else soc,'devm_usb_get_phy_by_phandle':-517 if case=='phy-defer' else phy,'devm_clk_get':clk,'clk_prepare':-5 if case=='prepare-fails' else 0,'clk_enable':-5 if case=='enable-fails' else 0,'clk_disable':0,'clk_unprepare':0,'ci_hdrc_add_device':-12 if case=='child-fails' else child,'dev_err':0}
 addresses={symbols[name]:name for name in returns}
 def code(uc,address,size,opaque):
  if address==callback:
   assert uc.reg_read(UC_ARM_REG_R0)==phy
   suspend=uc.reg_read(UC_ARM_REG_R1);assert suspend in [0,1];resumes.append(suspend)
   result=-110 if case=='resume-fails' and suspend==0 else 0
  elif address in addresses:
   name=addresses[address];calls.append(name);result=returns[name]
  else:return
  uc.reg_write(UC_ARM_REG_R0,result&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,code)
 u.reg_write(UC_ARM_REG_CPSR,0xd3);u.reg_write(UC_ARM_REG_SP,0x70008000)
 finish=0x7000f000;u.reg_write(UC_ARM_REG_LR,finish);u.reg_write(UC_ARM_REG_R0,pdev)
 u.emu_start(symbols['tegra_udc_probe'],finish,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==finish and u.reg_read(UC_ARM_REG_R0)==expected&0xffffffff
 assert resumes==([0] if case in ['success','resume-fails'] else [0,1] if case=='child-fails' else [])
 assert calls.count('ci_hdrc_add_device')==(1 if case in ['success','child-fails'] else 0)
 assert calls.count('clk_disable')==(1 if case in ['resume-fails','child-fails'] else 0)
 assert calls.count('clk_unprepare')==(1 if case in ['resume-fails','child-fails','enable-fails'] else 0)
 print('PASS compiled Tegra UDC probe:',case)
print('Actual probe flow executes; allocator, OF, clock, child registration and PHY callback are stubbed. No hardware is emulated.')
