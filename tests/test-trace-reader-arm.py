#!/usr/bin/env python3
"""Run the actual reader ELF with emulated syscalls; never touches a device."""
import argparse
from pathlib import Path
import struct
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_INTR, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_PROT_READ
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R7, UC_ARM_REG_SP, UC_CPU_ARM_CORTEX_A9

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('elf', type=Path)
args = p.parse_args()
elf = args.elf.read_bytes()
assert elf[:7] == b'\x7fELF\x01\x01\x01'
entry, phoff = struct.unpack_from('<II', elf, 24)
phsize, phnum = struct.unpack_from('<HH', elf, 42)
assert struct.unpack_from('<H', elf, 18)[0] == 40  # ARM
regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5]
trace = 0x40000000
payload = struct.pack('<32I', *range(32))

def run(case, expected, opt=True):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
    pages = set()
    segments = []
    for i in range(phnum):
        typ, off, va, pa, filesz, memsz, flags, align = struct.unpack_from('<8I', elf, phoff+i*phsize)
        if typ == 3:
            raise AssertionError('Reader must not need a dynamic linker')
        if typ != 1:
            continue
        segments.append((va, off, filesz))
        for page in range(va & ~4095, (va+memsz+4095) & ~4095, 4096):
            if page not in pages:
                u.mem_map(page, 4096)
                pages.add(page)
    for va, off, length in segments:
        u.mem_write(va, elf[off:off+length])
    u.mem_map(0x70000000, 0x10000)
    sp = 0x70008000
    argv = [b'reader\0'] + ([b'--read-reserved-trace\0'] if opt else [])
    pointers = []
    for i, arg in enumerate(argv):
        address = sp + 0x100 + i*128
        u.mem_write(address, arg)
        pointers.append(address)
    u.mem_write(sp, struct.pack('<'+'I'*(len(pointers)+2), len(pointers), *pointers, 0))
    u.reg_write(UC_ARM_REG_SP, sp)
    state = dict(open=False, mapped=False, closed=False, calls=[], reads=0,
                 stdout=bytearray(), stderr=bytearray(), exit=None, interrupted=False)
    def cstring(address):
        out = bytearray()
        for i in range(256):
            value = bytes(u.mem_read(address+i, 1))
            if value == b'\0':
                return out.decode()
            out.extend(value)
        raise AssertionError('unterminated pathname')
    def interrupt(uc, number, opaque):
        assert number == 2
        nr = uc.reg_read(UC_ARM_REG_R7)
        a = [uc.reg_read(reg) for reg in regs]
        state['calls'].append(nr)
        result = 0
        if nr == 5:
            assert opt and cstring(a[0]) == '/dev/mem'
            assert a[1:] == [0o4010000, 0, 0, 0, 0]  # O_RDONLY|O_SYNC
            result = -13 if case == 'open-error' else 9
            state['open'] = result == 9
        elif nr == 192:
            assert state['open'] and a == [0, 4096, 1, 1, 9, 0x1fe00]
            if case == 'mmap-error':
                result = -22
            else:
                u.mem_map(trace, 4096, UC_PROT_READ)
                u.mem_write(trace, payload + b'\xa5'*(4096-128))
                state['mapped'] = True
                result = trace
        elif nr == 91:
            assert state['mapped'] and a[:2] == [trace, 4096]
            assert state['reads'] == 64
            assert bytes(u.mem_read(trace+128, 4096-128)) == b'\xa5'*(4096-128)
            u.mem_unmap(trace, 4096)
            state['mapped'] = False
            result = -22 if case == 'unmap-error' else 0
        elif nr == 6:
            assert state['open'] and a[0] == 9
            state['closed'] = True
            result = -5 if case == 'close-error' else 0
        elif nr == 4:
            fd, address, count = a[:3]
            assert fd in (1, 2)
            assert not (trace <= address < trace+4096)
            if opt and fd == 1:
                assert state['closed'] and not state['mapped']
            if case == 'stdout-error' and fd == 1:
                result = 0
            elif case == 'short-eintr' and fd == 1 and not state['interrupted']:
                state['interrupted'] = True
                result = -4
            else:
                result = min(count, 7) if case == 'short-eintr' and fd == 1 else count
                state['stdout' if fd == 1 else 'stderr'].extend(u.mem_read(address, result))
        elif nr == 248:
            state['exit'] = a[0]
            uc.emu_stop()
            return
        else:
            raise AssertionError(('Forbidden syscall', nr))
        uc.reg_write(UC_ARM_REG_R0, result & 0xffffffff)
    def read(uc, access, address, size, value, opaque):
        if trace <= address < trace+4096:
            assert state['mapped'] and size == 4 and address < trace+128
            assert address == trace + (state['reads'] % 32)*4
            state['reads'] += 1
            if case == 'unstable' and state['reads'] == 33:
                uc.mem_write(trace, b'\xff'*4)
    def write(uc, access, address, size, value, opaque):
        assert not (address < trace+4096 and address+size > trace)
    u.hook_add(UC_HOOK_INTR, interrupt)
    u.hook_add(UC_HOOK_MEM_READ, read)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(entry, 0, count=100000)
    assert state['exit'] == expected, (case, state)
    if case in ('success', 'short-eintr'):
        assert bytes(state['stdout']) == payload
    elif opt:
        assert not state['stdout'], case
    else:
        assert state['calls'] == [4, 248]
        assert b'no device opened' in state['stdout']
    assert 3 not in state['calls'] and 180 not in state['calls']  # read/pread64
    print(case + ': passed')

for case, expected, opt in [('default-plan',0,False), ('success',0,True),
                           ('open-error',3,True), ('mmap-error',4,True),
                           ('unmap-error',5,True), ('close-error',5,True),
                           ('unstable',6,True), ('short-eintr',0,True),
                           ('stdout-error',7,True)]:
    run(case, expected, opt)
print('PASS: 9 compiled ARM reader scenarios. No real kernel mapping or device access was performed.')
