#!/usr/bin/env python3
"""Execute entry through CPU setup, including section transitions and HYP stub.

The legacy flag reproduces the tested image's executed literal pool offline.
No device access. Cache effects and full kernel boot are outside this test.
"""
import argparse
from pathlib import Path
import struct
import subprocess
import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('build', type=Path)
p.add_argument('--expect-old-pool-trap', action='store_true')
args = p.parse_args()
blob = (args.build/'out/arch/arm/boot/zImage').read_bytes()
syms = {}
for line in subprocess.check_output([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-nm'), '-n', str(args.build/'out/arch/arm/boot/compressed/vmlinux')], text=True).splitlines():
    parts = line.split()
    if len(parts) == 3:
        syms[parts[2]] = int(parts[0], 16)
config = (args.build/'out/.config').read_text().splitlines()
cookie = int(next(x.split('=',1)[1] for x in config if x.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=')),0)
pool = struct.pack('<4I', 0x1fe00000, cookie, 0xdeadffff, 0x584f4f4d)
pooloff = blob.index(pool, 0, 1024)
base = 0x1fe00000
end = syms.get('wingray_trace_mode_end', pooloff+len(pool)+0x80)
for load in [0x10008000, 0x00a00800]:
    for flags in range(16):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
        low = load & ~4095
        u.mem_map(low, (load-low+len(blob)+4095)//4096*4096)
        u.mem_write(load, blob)
        u.mem_map(base,4096)
        u.mem_write(base,b'\xa5'*4096)
        u.reg_write(UC_ARM_REG_CPSR,0xd3|(flags<<28))
        u.reg_write(UC_ARM_REG_R0,0)
        u.reg_write(UC_ARM_REG_R1,0xa49)
        u.reg_write(UC_ARM_REG_R2,0x100)
        # Unmapped stack: entry must not require a working stack yet.
        u.reg_write(UC_ARM_REG_SP,0x90000000)
        state = {'literal_executed':False}
        def code(uc,address,size,opaque):
            if load+pooloff <= address < load+pooloff+len(pool):
                state['literal_executed'] = True
                if not args.expect_old_pool_trap:
                    raise AssertionError('CPU executed literal pool at '+hex(address))
                uc.emu_stop()
        def write(uc,access,address,size,value,opaque):
            assert base <= address and address+size <= base+128
        u.hook_add(UC_HOOK_CODE, code)
        u.hook_add(UC_HOOK_MEM_WRITE, write)
        u.emu_start(load, load+end, count=10000)
        data = bytes(u.mem_read(base,4096))
        word = lambda off: struct.unpack_from('<I',data,off)[0]
        assert (word(0),word(4),word(8)) == (0x584f4f4d,1,cookie)
        assert data[128:] == b'\xa5'*(4096-128)
        if args.expect_old_pool_trap:
            assert state['literal_executed']
            assert word(0x28) == 0
        else:
            assert not state['literal_executed']
            assert u.reg_read(UC_ARM_REG_PC) == load+end
            assert word(0x28) == 1 and word(0x24) != 0
            assert (word(0x10),word(0x14),word(0x18)) == (0,0xa49,0x100)
            assert u.reg_read(UC_ARM_REG_R7) == 0xa49
            assert u.reg_read(UC_ARM_REG_R8) == 0x100
            assert u.reg_read(UC_ARM_REG_CPSR)&0xff == 0xd3
print(('REPRODUCED old executed-pool defect' if args.expect_old_pool_trap else 'PASS entry-to-mode flow') + ': 32 Cortex-A9 executions at header and observed PC-derived load bases.')
