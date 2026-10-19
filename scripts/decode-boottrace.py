#!/usr/bin/env python3
"""Decode a local Wingray RAM trace. Never contacts a device."""
from pathlib import Path
import argparse,json,struct
p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('--expected-cookie',type=lambda s:int(s,0),default=0x584d0001);args=p.parse_args()
data=args.snapshot.read_bytes()
if len(data)<128:p.error('Need at least 128 bytes from physical 0x1fe00000.')
w=struct.unpack_from('<32I',data)
valid=w[0]==0x584f4f4d and w[1] in (1,2) and w[2]==args.expected_cookie
stages=[('normalized_cpu_mode',0x28,1),('atag_conversion_returned',0x34,2),('before_decompression',0x38,3),('decompression_returned',0x3c,4),('kernel_stext',0x40,5),('before_mmu_enable',0x44,6),('tegra_init_early',0x48,7),('early_initcall',0x4c,8)]
result={'valid':valid,'magic':hex(w[0]),'format':w[1],'cookie':hex(w[2]),'expected_cookie':hex(args.expected_cookie),'limits':'A matching build cookie is not a unique boot-attempt identifier; exclude stale records before interpretation.'}
if valid:
 if w[1]>=2:
  stages += [('mmu_switched_entry',0x50,9),('bss_cleared',0x54,10),('start_kernel_entry',0x58,11),('setup_arch_entry',0x5c,12),('machine_selected',0x60,13),('before_paging_init',0x64,14)]
 result['entry']={name:hex(w[off//4]) for name,off in [('pc',0x0c),('r0',0x10),('r1',0x14),('r2',0x18),('cpsr',0x1c),('sctlr_after_mode_setup',0x20),('cpuid_after_mode_setup',0x24),('fdt_pointer',0x30)]}
 if w[0x28//4]!=1:
  result['entry']['sctlr_after_mode_setup']=None
  result['entry']['cpuid_after_mode_setup']=None
 if w[0x34//4]!=2:result['entry']['fdt_pointer']=None
 result['raw_atag_status_word']=hex(w[0x2c//4])
 result['atag_return_code']=None if w[1]<2 or w[0x34//4]!=2 or w[0x2c//4]==0xdeadffff else struct.unpack_from('<i',data,0x2c)[0]
 if w[1]==1:result['atag_status_warning']='Format 1 records r0 after fallback argument setup; it is not a reliable converter status.'
 if w[1]>=2 and w[0x44//4]==6:
  result['mmu_handoff']={name:hex(w[off//4]) for name,off in [('requested_sctlr',0x68),('boot_data',0x6c),('ttbr',0x70),('virtual_jump',0x74)]}
 if w[1]>=2:
  phases={0x101:'paging_init_entry',0x102:'memory_types_ready',0x103:'static_io_mapping_installed',0x104:'device_mappings_ready',0x105:'kmap_ready',0x106:'bootmem_ready',0x201:'paging_init_returned',0x202:'resources_requested',0x203:'device_tree_unflattened',0x204:'cpu_maps_ready',0x205:'psci_ready',0x206:'xen_early_returned',0x207:'hyp_mode_check_returned',0x208:'crashkernel_reserved',0x209:'before_machine_init_early',0x20a:'machine_init_early_returned',0x301:'tegra_init_early_entry',0x302:'trusted_foundations_returned',0x303:'cpu_reset_handler_ready',0x304:'flowctrl_ready',0x401:'setup_arch_returned'}
  result['last_phase']={'raw':hex(w[0x78//4]),'name':phases.get(w[0x78//4],'not_recorded' if w[0x78//4]==0 else 'unknown')}
 result['stages']={name:w[off//4]==expected for name,off,expected in stages}
print(json.dumps(result,indent=2))
raise SystemExit(0 if valid else 2)
