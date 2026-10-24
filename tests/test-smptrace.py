#!/usr/bin/env python3
"""Run actual linked reset instrumentation under ARM emulation; no hardware."""
from pathlib import Path
import argparse,importlib.util,struct,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('build',type=Path);p.add_argument('--cookie',type=lambda v:int(v,0),default=0x584d0037);a=p.parse_args()
symbols={line.split()[-1]:int(line.split()[0],16) for line in (a.build/'out/System.map').read_text().splitlines() if len(line.split())==3}
image=(a.build/'out/arch/arm/boot/Image').read_bytes();base=symbols['__tegra_cpu_reset_handler_start'];end=symbols['__tegra_cpu_reset_handler_end'];entry=symbols['__tegra_cpu_reset_handler']-base;data=symbols['__tegra_cpu_reset_handler_data']-base
code=image[base-0xc0008000:end-0xc0008000];assert 0<len(code)<=1024
# First conditional skip in the instrumented entry targets the end of tracing.
branch=struct.unpack_from('<I',code,entry+16)[0];assert branch>>24==0x0a
imm=branch&0xffffff;imm=imm-(1<<24) if imm&(1<<23) else imm
done=entry+16+8+imm*4;assert entry<done<data
cases=[('valid',1,True,0x58534d50,1,a.cookie,True),('cpu0',0,True,0x58534d50,1,a.cookie,False),('other-board',1,False,0,0,0,False),('bad-magic',1,True,0,1,a.cookie,False),('bad-version',1,True,0x58534d50,2,a.cookie,False),('bad-cookie',1,True,0x58534d50,1,a.cookie^1,False)]
for name,cpu,enabled,magic,version,cookie,expect in cases:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
    u.mem_map(0x40000000,4096);u.mem_write(0x40000000,code)
    u.mem_write(0x40000000+data+24,struct.pack('<I',0x1fe00000 if enabled else 0))
    if enabled:
        u.mem_map(0x1fe00000,4096);u.mem_write(0x1fe00000,struct.pack('<3I',magic,version,cookie))
    # Unicorn's A9 MPIDR is read-only CPU0. Supply only this hardware input;
    # execute every guard/store/barrier from the actual linked kernel bytes.
    def cpuid(uc,address,size,opaque):
        if struct.unpack('<I',uc.mem_read(address,4))[0]==0xee101fb0:
            uc.reg_write(UC_ARM_REG_R1,0x80000000|cpu)
            uc.reg_write(UC_ARM_REG_PC,address+4)
    u.hook_add(UC_HOOK_CODE,cpuid)
    for reg in range(UC_ARM_REG_R3,UC_ARM_REG_R12+1):u.reg_write(reg,0x12340000+reg)
    writes=[]
    u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,addr,size,value,opaque:writes.append((addr,size,value)))
    u.emu_start(0x40000000+entry,0x40000000+done,count=100)
    assert u.reg_read(UC_ARM_REG_PC)==0x40000000+done,name
    assert writes==([(0x1fe00014,4,1)] if expect else []),(name,writes)
    for reg in range(UC_ARM_REG_R3,UC_ARM_REG_R12+1):assert u.reg_read(reg)==0x12340000+reg,name
spec=importlib.util.spec_from_file_location('decoder',root/'scripts/decode-smptrace.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
w=[0]*32;w[:3]=[0x58534d50,1,0x584d0037];w[4]=17;w[5]=1;w[6]=5;w[10]=1
assert m.decode(struct.pack('<32I',*w),0x584d0037)['cpu1_online_observed_by_cpu0'] is True
for at,value in [(0,0),(1,2),(2,1),(3,1),(4,99),(5,2),(6,99),(31,1)]:
    bad=w.copy();bad[at]=value
    try:m.decode(struct.pack('<32I',*bad),0x584d0037)
    except ValueError:pass
    else:raise AssertionError(('decoder accepted invalid record',at))
print('PASS: actual ARM reset trace guards, single-word write, register preservation, IRAM size and decoder rejection checks; hardware untested.')
