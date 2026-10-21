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
 if w[1]>=2 and w[0x0c//4]==0x55534631:
  result['entry']={'register_words_reused':True,'fdt_pointer':result['entry']['fdt_pointer']}
  result['init_user_fault']={
   'pc':hex(w[0x10//4]),'address':hex(w[0x14//4]),
   'fsr':hex(w[0x18//4]),'cpsr':hex(w[0x1c//4]),
   'thumb':bool(w[0x1c//4]&0x20),'signal':w[0x20//4],
   'signal_code':struct.unpack_from('<i',data,0x24)[0],
   'note':'First observed PID 1 ARM userspace page fault before signal delivery; a handler could recover. Entry-register words are replaced, not a kernel fatal-PC record.'}
 if w[1]>=2 and w[0x0c//4]==0x554c4e31:
  result['entry']={'register_words_reused':True,'fdt_pointer':result['entry']['fdt_pointer']}
  link={}
  labels={'core_probe':{3:'map_registers',4:'hardware_init',5:'phy_init',6:'irq_lookup',7:'gadget_init',8:'otg_init',9:'role_start',10:'request_irq_or_finish'},'gadget_bind':{3:'allocate_strings',4:'register_serial_function'}}
  for name,off in [('core_probe',0x10),('gadget_bind',0x14)]:
   value=w[off//4]
   status={'raw':hex(value),'state':{0:'not_observed',1:'entered_or_pending',2:'returned_success'}.get(value,'at_stage')}
   if value&0x80000000:status.update(state='returned_error',errno=value&0xffff,stage=(value>>16)&0x7fff)
   elif value>2:status['stage']=value
   if 'stage' in status:status['stage_name']=labels[name].get(status['stage'],'entry' if status['stage']==1 else 'unknown')
   link[name]=status
  state=w[0x18//4]
  link['connection_snapshot']={'raw_state':hex(state),'observed':bool(state or w[0x1c//4] or w[0x20//4] or w[0x24//4]),'vbus_active':bool(state&1),'otg_capable':bool(state&2),'gadget_driver_attached':bool(state&4),'gadget_role':bool(state&8),'otgsc':hex(w[0x1c//4]),'b_session_valid':bool(w[0x1c//4]&0x800),'usbcmd':hex(w[0x20//4]),'run_stop':bool(w[0x20//4]&1),'usbmode':hex(w[0x24//4]),'controller_mode':{0:'idle',2:'device',3:'host'}.get(w[0x24//4]&3,'reserved')}
  link['limits']='Entry registers replaced. Probe and binding results are distinct; connection registers are sampled at active-clock driver checkpoints, not continuous telemetry. A userspace fault supersedes this record.'
  result['usb_link']=link
 result['raw_atag_status_word']=hex(w[0x2c//4])
 result['atag_return_code']=None if w[1]<2 or w[0x34//4]!=2 or w[0x2c//4]==0xdeadffff else struct.unpack_from('<i',data,0x2c)[0]
 if w[1]==1:result['atag_status_warning']='Format 1 records r0 after fallback argument setup; it is not a reliable converter status.'
 init_exit_record=w[1]>=2 and w[0x74//4]==0x58495431 and w[0x7c//4]==0xbad00001
 if init_exit_record:
  code=w[0x68//4];sig=code & 0x7f
  result['init_exit']={'wait_status':hex(code),'terminating_signal':sig,'core_dumped':bool(code & 0x80),'exit_status':(code>>8)&0xff if sig==0 else None,'note':'Recorded on the PID 1 death path before panic; replaces active-zone metadata.'}
 panic_message_record=w[1]>=2 and w[0x74//4]==0x504e4331 and w[0x7c//4]==0xbad00001
 if panic_message_record:
  result['panic_message']={'prefix':data[0x68:0x74].split(b'\0',1)[0].decode('ascii',errors='replace'),'maximum_bytes':12,'possibly_truncated':b'\0' not in data[0x68:0x74],'note':'The panic prefix replaces post-paging zone metadata; it is not the full panic log.'}
 diagnostic_record=w[1]>=2 and w[0x74//4]==0x44494131
 if diagnostic_record:
  diagnostic={}
  labels={'usb_phy':{3:'utmi_setup',4:'dr_mode',5:'vbus_regulator',6:'phy_initialization',7:'phy_registration'},'usb_udc':{3:'phy_lookup',4:'clock_lookup',5:'clock_enable',6:'phy_resume_attempt',7:'chipidea_creation'},'userspace_mount':{}}
  for name,off in [('usb_phy',0x68),('usb_udc',0x6c),('userspace_mount',0x70)]:
   value=w[off//4];state={0:'not_observed',1:'entered',2:'returned_success'}.get(value,'at_stage')
   status={'raw':hex(value),'state':state}
   if value & 0x80000000:status.update(state='returned_error',errno=value&0xffff,stage=(value>>16)&0x7fff)
   elif value>2:status['stage']=value
   if 'stage' in status:status['stage_name']=labels[name].get(status['stage'],'entry' if status['stage']==1 else 'unknown')
   diagnostic[name]=status
  diagnostic['limits']='Last attempt statuses; mount scope is PID 1 or a direct child. Probe return success is not USB enumeration. Replaces early zone metadata within the same 128-byte record.'
  result['diagnostic']=diagnostic
 memmap_magic=0x574d4150
 memmap_extended=w[1]>=2 and (w[0x74//4]&0xff000000)==0x58000000 and w[0x74//4]!=0x58495431
 memmap_record=w[1]>=2 and (w[0x74//4]==memmap_magic or memmap_extended)
 if w[1]>=2 and w[0x44//4]==6 and not memmap_record and not panic_message_record and not init_exit_record and not diagnostic_record:
  result['mmu_handoff']={name:hex(w[off//4]) for name,off in [('requested_sctlr',0x68),('boot_data',0x6c),('ttbr',0x70),('virtual_jump',0x74)]}
 if memmap_record:
  info=w[0x74//4] if memmap_extended else w[0x70//4]
  context=info & 0xff
  result['memmap_zone']={'start_pfn':hex(w[0x68//4]),'end_pfn_exclusive':hex(w[0x6c//4]),'size_pfns':w[0x6c//4]-w[0x68//4],'nid':(info>>16)&0xff,'zone_index':(info>>8)&0xff,'context':{0:'early',1:'hotplug'}.get(context,'unknown_'+str(context)),'note':'This record replaces the MMU handoff words after paging is active; the earlier trace phases show that the handoff was passed.'}
  if memmap_extended:
   result['memmap_zone'].update(nid=(info>>20)&0xf,zone_index=(info>>16)&0xf,first_page_descriptor=hex(w[0x70//4]),page_descriptor_stride=(info>>8)&0xff)
 if w[1]>=2:
  phases={0x101:'paging_init_entry',0x102:'memory_types_ready',0x103:'static_io_mapping_installed',0x104:'device_mappings_ready',0x105:'kmap_ready',0x106:'bootmem_ready',0x201:'paging_init_returned',0x202:'resources_requested',0x203:'device_tree_unflattened',0x204:'cpu_maps_ready',0x205:'psci_ready',0x206:'xen_early_returned',0x207:'hyp_mode_check_returned',0x208:'crashkernel_reserved',0x209:'before_machine_init_early',0x20a:'machine_init_early_returned',0x301:'tegra_init_early_entry',0x302:'trusted_foundations_returned',0x303:'cpu_reset_handler_ready',0x304:'flowctrl_ready',0x401:'setup_arch_returned',0x402:'before_init_irq',0x403:'time_init_returned',0x404:'console_init_returned',0x405:'before_rest_init',0x406:'kernel_init_entry',0x410:'before_basic_setup',0x411:'basic_setup_returned',0x420:'before_init_exec',0x421:'init_exec_succeeded'}
  result['last_phase']={'raw':hex(w[0x78//4]),'name':phases.get(w[0x78//4],'not_recorded' if w[0x78//4]==0 else 'unknown')}
  more_phases={0x107:'tcm_init_returned',0x108:'zero_page_allocated',0x110:'bootmem_init_entry',0x111:'memory_limits_ready',0x112:'early_memtest_returned',0x113:'memory_present_returned',0x114:'sparse_init_returned',0x115:'zone_sizes_initialized'}
  more_phases.update({0x500:'zone_sizes_entry',0x501:'zone_sizes_ready',0x502:'zone_holes_ready',0x503:'before_free_area_init_node',0x504:'free_area_init_node_returned',0x510:'free_area_init_node_entry',0x511:'node_totals_ready',0x512:'node_map_returned',0x513:'node_map_printk_returned',0x514:'before_free_area_init_core',0x515:'free_area_init_core_returned',0x520:'alloc_node_mem_map_entry',0x521:'before_node_map_allocation',0x522:'node_map_allocation_returned',0x523:'node_map_pointer_stored',0x530:'free_area_init_core_entry'})
  more_phases.update({0x701:'memmap_init_zone_entry',0x702:'memmap_range_ready',0x703:'memmap_loop_returned',0x516:'memmap_init_returned'})
  if w[0x78//4] in more_phases:result['last_phase']['name']=more_phases[w[0x78//4]]
  phase=w[0x78//4]
  if (phase & 0xffff0000)==0xc1000000:
   result['last_phase'].update(name='init_exec_failed',errno=phase & 0xffff)
  zone_steps={1:'entry',2:'before_pcp_init',3:'pcp_init_returned',4:'before_setup_usemap',5:'setup_usemap_returned',6:'empty_zone_initialized',7:'memmap_init_returned'}
  if 0x600<=phase<0x650 and (phase & 15) in zone_steps:
   result['last_phase'].update(name='zone_'+zone_steps[phase & 15],zone_index=(phase-0x600)//16)
  fault=w[0x7c//4]
  result['first_fatal']={'raw':hex(fault),'kind':'not_recorded' if fault==0 else 'panic' if fault==0xbad00001 else 'kernel_die_pc'}
  page_steps={1:'before_pfn_validation',2:'pfn_validation_passed',3:'before_single_page_init',4:'single_page_init_returned',5:'before_pageblock_update',6:'pageblock_update_returned',8:'single_page_entry',9:'page_links_set',10:'page_count_initialized',11:'page_mapcount_reset',12:'page_cpupid_reset',13:'page_lru_initialized'}
  if (phase & 0xf0000000)==0x90000000:
   pfn=phase & 0x0fffffff
   result['last_phase'].update(name='memmap_progress_checkpoint',pfn=hex(pfn),physical_page=hex(pfn << 12),checkpoint=True)
  if (phase & 0xf0000000)==0xa0000000:
   pfn=phase & 0x0fffffff
   result['last_phase'].update(name='memmap_window_checkpoint',pfn=hex(pfn),physical_page=hex(pfn << 12),checkpoint=True,sampling='End of each 16-PFN block from 0x2ebf0 through 0x2ec2f; pages later in the current block may have executed.')
  if (phase & 0xf0000000)==0x80000000 and ((phase >> 24) & 15) in page_steps:
   pfn=phase & 0x00ffffff
   result['last_phase'].update(name=page_steps[(phase >> 24) & 15],pfn=hex(pfn),physical_page=hex(pfn << 12),sampling='Only PFNs with (pfn & 1023) < 4 are detailed; a later unsampled PFN may have executed.')
  if (phase & 0xf0000000)==0xb0000000 and (phase & 0x00ffffff)==0x2ec00 and ((phase>>24)&15) in range(1,7):
   pfn=phase & 0x00ffffff
   result['last_phase'].update(name='boundary_'+page_steps[(phase>>24)&15],pfn=hex(pfn),physical_page=hex(pfn<<12),sampling='Only PFN 0x2ec00 is bracketed; later work can execute before the next checkpoint.')
  if memmap_extended and 'pfn' in result['last_phase']:
   pfn=int(result['last_phase']['pfn'],16)
   stride=(info>>8)&0xff
   if w[0x68//4]<=pfn<w[0x6c//4] and stride:
    address=w[0x70//4]+(pfn-w[0x68//4])*stride
    if address<=0xffffffff:result['last_phase']['calculated_descriptor_address']=hex(address)
 result['stages']={name:w[off//4]==expected for name,off,expected in stages}
 if w[1]>=2 and w[0x48//4]==0x47504931:
  state=w[0x4c//4]
  result['usb_switch_gpio']={'raw':hex(state),'reserved_bits_zero':not bool(state&~0xff),'limits':'Snapshot after successful GPIO-controller registration. CNF/OE/OUT are register values; matching owner means requested under the expected board label. No input-level, pinmux tristate or electrical measurement. The two completed early-init marker words are replaced.'}
  for name,shift in [('data_enable_pv4',0),('forceon_n_pc5',4)]:
   result['usb_switch_gpio'][name]={'gpio_mode':bool(state&(1<<shift)),'output_enabled':bool(state&(2<<shift)),'output_high':bool(state&(4<<shift)),'requested_by_expected_owner':bool(state&(8<<shift))}
  result['stages']['tegra_init_early']=None
  result['stages']['early_initcall']=None

print(json.dumps(result,indent=2))
raise SystemExit(0 if valid else 2)
