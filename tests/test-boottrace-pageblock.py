#!/usr/bin/env python3
"""Run compiled memmap initialization including its real bitmap update.

The fixture supplies valid virtual page/zone/bitmap storage. Unicorn executes
the actual LDREX/STREX instructions; it does not model hardware cache attributes,
physical translations, reset retention, or the real boot allocator's pointers.
"""
from pathlib import Path
import argparse, re, shlex, struct, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('build', type=Path)
build = parser.parse_args().build.resolve()
prefix = root / 'toolchains/android-gcc49/bin/arm-linux-androideabi-'
elf = build / 'out/vmlinux'
symbols = {}
for line in subprocess.check_output([str(prefix)+'nm', '-n', str(elf)], text=True).splitlines():
    parts = line.split()
    if len(parts) == 3:
        symbols[parts[2]] = int(parts[0], 16)

# Compile structure offsets with this build's exact compiler flags and headers.
# No object is linked into the kernel and no layout is guessed by the fixture.
with tempfile.TemporaryDirectory(prefix='xoom-layout-') as temp:
    temp = Path(temp)
    probe = temp / 'layout.c'
    probe.write_text('''#include <linux/mm.h>
#include <linux/pageblock-flags.h>
const unsigned int layout_probe[] = {
 sizeof(struct page), offsetof(pg_data_t, node_zones), sizeof(struct zone),
 offsetof(struct zone, pageblock_flags), offsetof(struct zone, zone_start_pfn),
 offsetof(struct zone, spanned_pages), pageblock_nr_pages, NR_PAGEBLOCK_BITS,
 PB_migrate_end, MIGRATE_MOVABLE, MIGRATETYPE_MASK
};
''')
    raw_cmd = (build/'out/mm/.page_alloc.o.cmd').read_text().splitlines()[0].split(' := ', 1)[1]
    command = shlex.split(raw_cmd.replace('$(pound)', '#'))
    command = [('-Wp,-MD,'+str(temp/'layout.d')) if x.startswith('-Wp,-MD,') else x for x in command]
    command[command.index('-o')+1] = str(temp/'layout.o')
    command[-1] = str(probe)
    subprocess.run(command, cwd=build/'out', check=True, capture_output=True)
    subprocess.run([str(prefix)+'objcopy', '-j', '.rodata', '-O', 'binary', str(temp/'layout.o'), str(temp/'layout.bin')], check=True)
    layout = struct.unpack('<11I', (temp/'layout.bin').read_bytes())
stride, zones_off, zone_stride, bitmap_off, start_off, span_off, block_pages, bits_per_block, end_bit, movable, migrate_mask = layout
assert stride > 0 and block_pages > 0 and bits_per_block == 4

function = symbols['set_pfnblock_flags_mask']
function_size = next(int(line.split()[1], 16) for line in subprocess.check_output([str(prefix)+'nm', '-S', str(elf)], text=True).splitlines() if line.split()[-1] == 'set_pfnblock_flags_mask')
disasm = subprocess.check_output([str(prefix)+'objdump', '-d', '--start-address='+hex(function), '--stop-address='+hex(function+function_size), str(elf)], text=True)
exclusive = {int(m.group(1), 16): m.group(2) for m in re.finditer(r'^\s*([0-9a-f]+):\s+[0-9a-f]+\s+(ldrex|strex)(?:eq|ne)?\b', disasm, re.M)}
assert set(exclusive.values()) == {'ldrex', 'strex'}
image = (build/'out/arch/arm/boot/Image').read_bytes()
config = (build/'out/.config').read_text()
cookie = int(re.search(r'^CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=(.*)$', config, re.M)[1], 0)
assert 'CONFIG_FLATMEM=y' in config and 'CONFIG_SMP=y' not in config

for name, start, count in [('first-block', 0, 4), ('unaligned-zone-boundary', 0x2ebf0, 64), ('aligned-boundary', 0x2ec00, 1), ('multiple-blocks', 0, block_pages*2+1)]:
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
    u.mem_map(0xc0008000, (max(len(image), symbols['_end']-0xc0008000)+4095)//4096*4096)
    u.mem_write(0xc0008000, image)
    u.mem_map(0x70000000, 0x10000)
    storage = 0x71000000
    u.mem_map(storage, (count*stride+4095)//4096*4096)
    bitmap = 0x72000000
    u.mem_map(bitmap, 4096)
    u.mem_write(bitmap, b'\xa5'*4096)
    u.mem_map(0xfe600000, 4096)
    u.mem_write(0xfe600000, struct.pack('<3I', 0x584f4f4d, 2, cookie))
    u.mem_write(symbols['wingray_boottrace_static_ready'], b'\x01')
    u.mem_write(symbols['mem_map'], struct.pack('<I', storage-start*stride))
    zone = symbols['contig_page_data']+zones_off
    for address, value in [(zone+bitmap_off, bitmap), (zone+start_off, start), (zone+span_off, count)]:
        u.mem_write(address, struct.pack('<I', value))
    finish, stack = 0x7000f000, 0x70008000
    u.reg_write(UC_ARM_REG_CPSR, 0xd3)
    for reg, value in [(UC_ARM_REG_R0, count), (UC_ARM_REG_R1, 0), (UC_ARM_REG_R2, 0), (UC_ARM_REG_R3, start), (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, finish)]:
        u.reg_write(reg, value)
    u.mem_write(stack, struct.pack('<I', 0))
    counts = {'ldrex': 0, 'strex': 0, 'calls': 0}
    phases = []
    def code(uc, address, size, opaque):
        if address == symbols['set_pfnblock_flags_mask']:
            counts['calls'] += 1
        if address in exclusive:
            counts[exclusive[address]] += 1
            assert counts[exclusive[address]] < 100, (name, 'exclusive loop failed to finish')
    def write(uc, access, address, size, value, opaque):
        if 0x70000000 <= address and address+size <= 0x70010000: return
        if storage <= address and address+size <= storage+count*stride: return
        if bitmap <= address and address+size <= bitmap+4096: return
        if address == symbols['highest_memmap_pfn']: return
        assert address in (0xfe600068, 0xfe60006c, 0xfe600070, 0xfe600074, 0xfe600078) and size == 4, (name, hex(address), size)
        if address == 0xfe600078: phases.append(value)
    u.hook_add(UC_HOOK_CODE, code)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(symbols['memmap_init_zone'], finish, count=500000)
    assert u.reg_read(UC_ARM_REG_PC) == finish and phases[-1] == 0x703
    expected = bytearray(b'\xa5'*4096)
    blocks = [pfn for pfn in range(start, start+count) if pfn % block_pages == 0]
    for pfn in blocks:
        bit = ((pfn-(start//block_pages)*block_pages)//block_pages)*bits_per_block
        word_index, within_word = divmod(bit, 32)
        shift = 31-within_word-end_bit
        before = struct.unpack_from('<I', expected, word_index*4)[0]
        after = (before & ~(migrate_mask << shift)) | (movable << shift)
        struct.pack_into('<I', expected, word_index*4, after)
    assert bytes(u.mem_read(bitmap, 4096)) == expected, name
    assert counts['calls'] == len(blocks) and counts['ldrex'] >= len(blocks) and counts['strex'] >= len(blocks), (name, counts)
    if 0x2ec00 in range(start, start+count):
        assert [x for x in phases if x>>28 == 0xb] == [0xb002ec00|(step<<24) for step in range(1, 7)]
    print('PASS real pageblock update:', name, counts)
print('Actual bitmap/exclusive code executed; hardware memory attributes and allocator mappings remain untested.')
