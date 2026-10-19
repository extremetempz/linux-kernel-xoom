#!/usr/bin/env python3
"""Execute the built ARM trace snippets, not a reimplementation, on Cortex-A9.

Requires Unicorn 2.1.4. Cache/reset persistence is outside this test's scope.
"""
from pathlib import Path
import argparse, struct, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('build',type=Path);args=p.parse_args()
config=(args.build/'out/.config').read_text().splitlines()
cookie=int(next(line.split('=',1)[1] for line in config if line.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
version = int(next(x.split()[-1] for x in (args.build/'source/include/soc/tegra/wingray-boottrace.h').read_text().splitlines() if x.startswith('#define WINGRAY_TRACE_VERSION')))
nm=root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'
def symbols(path):
    result={}
    for line in subprocess.check_output([str(nm),str(path)],text=True).splitlines():
        parts=line.split()
        if len(parts)==3:result[parts[2]]=int(parts[0],16)
    return result
zs=symbols(args.build/'out/arch/arm/boot/compressed/vmlinux')
ks=symbols(args.build/'out/vmlinux')
z=(args.build/'out/arch/arm/boot/zImage').read_bytes()
k=(args.build/'out/arch/arm/boot/Image').read_bytes()
regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,
      UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,
      UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12,UC_ARM_REG_SP,UC_ARM_REG_LR]
base=0x1fe00000
cases=[('zentry',z,zs,0x10008000,0),('atag',z,zs,0x10008000,0),
       ('stext',k,ks,0x8000,0xc0008000),('mmu',k,ks,0x8000,0xc0008000)]
for name,blob,syms,load,link in cases:
    begin=load+syms['wingray_trace_'+name+'_begin']-link
    end=load+syms['wingray_trace_'+name+'_end']-link
    assert load<=begin<end<=load+len(blob)
    for flags in range(16):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
        u.mem_map(load,(len(blob)+4095)//4096*4096)
        u.mem_write(load,blob);u.mem_map(base,4096);u.mem_write(base,b'\xa5'*4096)
        u.reg_write(UC_ARM_REG_CPSR,0xd3|(flags<<28))
        initial=[0x11220000+i*0x101 for i in range(15)]
        initial[0]=0xfffffffd;initial[1]=2633;initial[2]=0x10000100;initial[6]=0x102e2a40
        for reg,value in zip(regs,initial):u.reg_write(reg,value)
        cpsr=u.reg_read(UC_ARM_REG_CPSR)
        writes=[]
        def check_write(uc,access,address,size,value,opaque):
            assert base<=address and address+size<=base+128, (name,hex(address),size)
            writes.append(address-base)
        u.hook_add(UC_HOOK_MEM_WRITE,check_write)
        u.emu_start(begin,end,count=10000)
        assert u.reg_read(UC_ARM_REG_PC)==end,name
        for i,reg in enumerate(regs):
            if i not in (3,12):assert u.reg_read(reg)==initial[i],(name,i)
        assert u.reg_read(UC_ARM_REG_CPSR)==cpsr,(name,'CPSR')
        data=bytes(u.mem_read(base,4096));word=lambda off:struct.unpack_from('<I',data,off)[0]
        assert data[128:]==b'\xa5'*(4096-128)
        if name=='zentry':
            assert word(0)==0x584f4f4d and word(4)==version and word(8)==cookie
            assert word(0x10)==initial[0] and word(0x14)==initial[1] and word(0x18)==initial[2]
            assert word(0x1c)==cpsr and begin<=word(0x0c)<end+8
            assert word(0x2c)==0xdeadffff
            assert all(word(off)==0 for off in range(0x30,128,4))
        elif name=='atag':
            assert word(0x2c)==initial[0] and word(0x30)==initial[6] and word(0x34)==2
            assert set(writes)=={0x2c,0x30,0x34}
        else:
            off,value=(0x40,5) if name=='stext' else (0x44,6)
            assert word(off)==value
            if name=='mmu' and version>=2:
                assert set(writes)=={0x44,0x68,0x6c,0x70,0x74}
                assert [word(o) for o in (0x68,0x6c,0x70,0x74)]==[initial[i] for i in (0,2,4,13)]
            else:assert writes==[off]
    print(name+': compiled Cortex-A9 snippet passed 16 flag patterns; boot registers preserved; writes confined to trace window.')
print('PASS: 64 ARM snippet executions. This does not simulate the full kernel or prove hardware cache/reset retention.')
