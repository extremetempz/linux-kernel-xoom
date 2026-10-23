#!/usr/bin/env python3
"""Measure actual Motorola/Decatf framebuffer declarations using existing ARM ABI tooling.

Offline only: reads committed GPL headers, compiles ARM constant objects, never
runs generated code or accesses a device. Matching numbers are not a semantic verdict.
"""
import argparse,importlib.util,json,re,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('graphics_abi',ROOT/'scripts/audit-tegra-graphics-abi.py')
abi=importlib.util.module_from_spec(spec);spec.loader.exec_module(abi)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--save-dir',type=Path,required=True);a=p.parse_args()
 if a.save_dir.exists():p.error('Require a new evidence directory')
 cc=ROOT/'toolchains/android-gcc49/bin/arm-linux-androideabi-gcc'
 specs=[('motorola',ROOT/'sources/kernel-baseline',abi.PINS['baseline'],'include/video/tegrafb.h',True),('elementalx',ROOT/'sources/kernel-elementalx-review',abi.PINS['elementalx'],'include/video/tegrafb.h',True),('decatf',ROOT/'sources/kernel-donor',abi.PINS['donor_base'],'drivers/staging/tegra/include/video/tegrafb.h',False),('wingray_current',ROOT/'sources/kernel-donor','HEAD','drivers/staging/tegra/include/video/tegrafb.h',False)]
 results={}
 with tempfile.TemporaryDirectory(prefix='xoom-fb-abi-') as temp:
  t=Path(temp)
  for name,repo,revision,path,original in specs:
   revision=abi.resolve(repo,revision);header,meta=abi.source(repo,revision,path)
   body=re.sub(r'^\s*#include[^\n]*\n','',header,flags=re.M)
   if re.search(r'^\s*#\s*include\b',body,re.M):raise ValueError('Unreviewed include')
   ioctl,_=abi.source(repo,revision,'include/asm-generic/ioctl.h' if original else 'include/uapi/asm-generic/ioctl.h')
   names=re.findall(r'^#define (FBIO_TEGRA_\w+)\s+_IO\w*\(',body,re.M)
   structs=re.findall(r'^struct (tegra_fb_\w+)\s*\{',body,re.M)
   assert names and structs and len(names)<32 and len(structs)<16
   fields={}
   for struct in structs:
    declaration=re.search(r'^struct '+re.escape(struct)+r'\s*\{(.*?)\};',body,re.M|re.S).group(1)
    members=re.findall(r'^\s*(?:__s32|__u32|struct fb_var_screeninfo\s*\*)\s*(\w+)(?:\[[^\]]+\])?\s*;',declaration,re.M)
    # The flip's nested window array uses a different type; include it too.
    members+=re.findall(r'^\s*struct tegra_fb_windowattr\s+(\w+)\[[^\]]+\];',declaration,re.M)
    fields.update({struct+'.'+n:f'__builtin_offsetof(struct {struct}, {n})' for n in members})
   expressions=names+[f'sizeof(struct {n})' for n in structs]+list(fields.values())
   source=abi.TYPE_PREFIX+ioctl+'\n'+body+'\n__attribute__((used,section(".xoom_abi"))) const unsigned int values[] = {'+','.join(expressions)+'};\n'
   c=t/(name+'.c');obj=t/(name+'.o');c.write_text(source);abi.run([cc,*abi.FLAGS,'-c',c,'-o',obj])
   v=abi.elf_values(obj,len(expressions));results[name]={'revision':revision,'header':meta,'ioctls':{n:f'0x{x:08x}' for n,x in zip(names,v)},'struct_sizes':dict(zip(structs,v[len(names):len(names)+len(structs)])),'field_offsets':dict(zip(fields,v[len(names)+len(structs):]))}
   a.save_dir.mkdir(parents=True,exist_ok=True);(a.save_dir/c.name).write_bytes(c.read_bytes());(a.save_dir/obj.name).write_bytes(obj.read_bytes())
  common=set.intersection(*(set(x['ioctls']) for x in results.values()))
  missing=sorted(set(results['elementalx']['ioctls'])-set(results['decatf']['ioctls']))
  current_missing=sorted(set(results['elementalx']['ioctls'])-set(results['wingray_current']['ioctls']))
  report={'measurements':results,'common_ioctls_equal':all(len({x['ioctls'][n] for x in results.values()})==1 for n in common),'missing_original_ioctls_in_donor':missing,'missing_original_ioctls_in_current_declarations':current_missing,'current_original_ioctls_equal':all(results['wingray_current']['ioctls'].get(n)==v for n,v in results['elementalx']['ioctls'].items()),'hardware_compatibility_established':False,'limits':['ARM32 declarations/encoding only; no library execution, allocation, flip, fence or hardware behavior tested.','Do not synthesize successful flips or replace post-syncpoint completion with an immediate signal.']}
  reference=results['elementalx']
  assert reference['ioctls']=={'FBIO_TEGRA_SET_NVMAP_FD':'0x40044640','FBIO_TEGRA_FLIP':'0x41044641','FBIO_TEGRA_GET_MODEDB':'0xc0084642'}
  assert reference['struct_sizes']=={'tegra_fb_windowattr':84,'tegra_fb_flip_args':260,'tegra_fb_modedb':8}
  assert reference['field_offsets']['tegra_fb_flip_args.post_syncpt_id']==252
  assert reference['field_offsets']['tegra_fb_flip_args.post_syncpt_val']==256
  assert reference['field_offsets']['tegra_fb_windowattr.pre_syncpt_id']==76
  assert reference['field_offsets']['tegra_fb_windowattr.pre_syncpt_val']==80
  for key in ['ioctls','struct_sizes','field_offsets']:
   assert results['motorola'][key]==reference[key],key
  (a.save_dir/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
