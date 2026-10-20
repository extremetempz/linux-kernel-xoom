#!/usr/bin/env python3
"""Execute extracted production ARM limit/zone sizing with controlled RAM banks.

The fixture runs the actual find_limits() and zone_sizes_init() bodies on a
32-bit Cortex-A9 model. It does not emulate memblock allocation or real MMU.
"""
from pathlib import Path
import re, struct, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'toolchains/trace-test/site-packages'))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_INVALID
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_CPSR, UC_CPU_ARM_CORTEX_A9

source = (root/'sources/kernel-donor/arch/arm/mm/init.c').read_text()
def function(name):
    start = source.index('static void __init '+name+'(')
    brace = source.index('{', start)
    depth = 1
    end = brace+1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

bodies = function('find_limits')+'\n'+function('zone_sizes_init')
fix = '\t*max_low = min(*max_low, *max_high);'
assert bodies.count(fix) == 1
prefix = str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-')
fixture = r'''
#define __init
#define CONFIG_HIGHMEM 1
#define MAX_NR_ZONES 2
#define ZONE_HIGHMEM 1
#define PAGE_SHIFT 12
#define PFN_DOWN(x) ((x) >> PAGE_SHIFT)
#define PFN_UP(x) (((x) + 4095UL) >> PAGE_SHIFT)
#define min(a,b) ((a) < (b) ? (a) : (b))
#define max(a,b) ((a) > (b) ? (a) : (b))
#define wingray_boottrace_static_mark(a,b) do {} while (0)
typedef unsigned long phys_addr_t;
struct memblock_region { unsigned long base, size; };
struct memblock_region banks[8];
unsigned long bank_count, ceiling, report[8];
#define for_each_memblock(kind, reg) for ((reg)=banks; (reg)<banks+bank_count; (reg)++)
#define memblock_region_memory_base_pfn(r) PFN_UP((r)->base)
#define memblock_region_memory_end_pfn(r) PFN_DOWN((r)->base+(r)->size)
unsigned long memblock_get_current_limit(void) { return ceiling; }
unsigned long memblock_start_of_DRAM(void) { return banks[0].base; }
unsigned long memblock_end_of_DRAM(void) { return banks[bank_count-1].base+banks[bank_count-1].size; }
void *memset(void *p, int c, unsigned n) { unsigned char *q=p; while(n--) *q++=c; return p; }
void *memcpy(void *d, const void *s, unsigned n) { unsigned char *q=d; const unsigned char *p=s; while(n--) *q++=*p++; return d; }
void free_area_init_node(int nid, unsigned long *zones, unsigned long first, unsigned long *holes) {
 report[3]=zones[0]; report[4]=zones[1]; report[5]=holes[0]; report[6]=holes[1];
 report[7]=zones[0]+zones[1];
}
'''
wrapper = r'''
void run(void) {
 unsigned long first, low, high;
 find_limits(&first, &low, &high);
 report[0]=first; report[1]=low; report[2]=high;
 zone_sizes_init(first, low, high);
}
'''
cases = [
 ('xoom-top-no-map',0x30000000,[(0x1000,0x1fdff000),(0x20000000,0xe800000)]),
 ('ordinary-highmem',0x30000000,[(0,0x40000000)]),
 ('exact-lowmem',0x30000000,[(0,0x30000000)]),
 ('small-ram',0x30000000,[(0,0x10000000)]),
 ('unaligned-removed-top',0x30000000,[(0x1000,0x1fdff000),(0x20000000,0xe827000)]),
 ('highmem-with-hole',0x30000000,[(0x1000,0x1fdff000),(0x20000000,0xe800000),(0x38000000,0x8000000)]),
]
with tempfile.TemporaryDirectory(prefix='xoom-limits-') as tmp:
    tmp = Path(tmp)
    for mode, body in [('old', bodies.replace(fix, '')), ('corrected', bodies)]:
        c = tmp/(mode+'.c'); elf = tmp/(mode+'.elf'); binary = tmp/(mode+'.bin')
        c.write_text(fixture+body+wrapper)
        subprocess.run([prefix+'gcc','-march=armv7-a','-marm','-mfloat-abi=soft','-Os',
          '-ffreestanding','-fno-pic','-fno-pie','-fno-builtin','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
          '-nostdlib','-Wl,--build-id=none','-Wl,-Ttext=0x10000','-Wl,--entry=run',str(c),'-o',str(elf)],check=True,capture_output=True)
        subprocess.run([prefix+'objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True)
        sections = subprocess.check_output([prefix+'objdump','-h',str(elf)],text=True)
        text_start = int(re.search(r'\s+\d+ \.text\s+\S+\s+(\S+)', sections)[1],16)
        symbols = {}
        for line in subprocess.check_output([prefix+'nm','-n',str(elf)],text=True).splitlines():
            parts=line.split()
            if len(parts)==3: symbols[parts[2]]=int(parts[0],16)
        for name, ceiling, banks in cases:
            u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A9)
            u.mem_map(0x10000,0x20000); u.mem_write(text_start,binary.read_bytes())
            u.mem_map(0x70000000,0x10000)
            u.mem_write(symbols['banks'],b''.join(struct.pack('<II',*bank) for bank in banks))
            u.mem_write(symbols['bank_count'],struct.pack('<I',len(banks)))
            u.mem_write(symbols['ceiling'],struct.pack('<I',ceiling))
            u.reg_write(UC_ARM_REG_CPSR,0xd3); u.reg_write(UC_ARM_REG_SP,0x70008000)
            finish=0x7000f000; u.reg_write(UC_ARM_REG_LR,finish)
            def invalid(uc, access, address, size, value, data):
                print('unmapped fixture access',hex(uc.reg_read(UC_ARM_REG_PC)),hex(address),symbols,flush=True)
                return False
            u.hook_add(UC_HOOK_MEM_INVALID,invalid)
            u.emu_start(symbols['run'],finish,count=10000)
            assert u.reg_read(UC_ARM_REG_PC)==finish
            first,low,high,normal,highmem,holes0,holes1,total=struct.unpack('<8I',u.mem_read(symbols['report'],32))
            actual_high=(banks[-1][0]+banks[-1][1])>>12
            actual_first=(banks[0][0]+4095)>>12
            expected_low=min(ceiling>>12,actual_high)
            if mode=='old' and ceiling>>12>actual_high:
                assert low>high and highmem>0x80000000
                # Allocation covers total PFNs; Normal initialization exceeds it.
                assert first+normal>first+total
                print('REPRODUCED old unsigned underflow and descriptor overrun:',name,
                      'normal_end='+hex(first+normal),'node_end='+hex(first+total))
                continue
            assert (first,low,high)==(actual_first,expected_low,actual_high)
            assert normal==low-first and highmem==high-low
            assert total==high-first and first+normal<=first+total
            present=sum(size>>12 for base,size in banks)
            assert normal-holes0+highmem-holes1==present
            assert holes0<=normal and holes1<=highmem
            print('PASS',mode,name)
print('Production ARM sizing executed; no allocator or physical mapping emulated.')
