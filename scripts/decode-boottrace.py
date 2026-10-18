#!/usr/bin/env python3
"""Decode a local Wingray RAM trace. Never contacts a device."""
from pathlib import Path
import argparse,json,struct
p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('--expected-cookie',type=lambda s:int(s,0),default=0x584d0001);args=p.parse_args()
data=args.snapshot.read_bytes()
if len(data)<128:p.error('Need at least 128 bytes from physical 0x1fe00000.')
w=struct.unpack_from('<32I',data)
valid=w[0]==0x584f4f4d and w[1]==1 and w[2]==args.expected_cookie
stages=[('normalized_cpu_mode',0x28,1),('atag_conversion_returned',0x34,2),('before_decompression',0x38,3),('decompression_returned',0x3c,4),('kernel_stext',0x40,5),('before_mmu_enable',0x44,6),('tegra_init_early',0x48,7),('early_initcall',0x4c,8)]
result={'valid':valid,'magic':hex(w[0]),'format':w[1],'cookie':hex(w[2]),'expected_cookie':hex(args.expected_cookie),'limits':'A matching build cookie is not a unique boot-attempt identifier; exclude stale records before interpretation.'}
if valid:
 result['entry']={name:hex(w[off//4]) for name,off in [('pc',0x0c),('r0',0x10),('r1',0x14),('r2',0x18),('cpsr',0x1c),('sctlr_after_mode_setup',0x20),('cpuid_after_mode_setup',0x24),('fdt_pointer',0x30)]}
 result['atag_return_code']=None if w[0x2c//4]==0xdeadffff else struct.unpack_from('<i',data,0x2c)[0]
 result['stages']={name:w[off//4]==expected for name,off,expected in stages}
print(json.dumps(result,indent=2))
raise SystemExit(0 if valid else 2)
