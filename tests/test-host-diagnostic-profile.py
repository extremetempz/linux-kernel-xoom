#!/usr/bin/env python3
"""Reject unsafe DT/config mutations and verify the actual packaged boot image."""
from pathlib import Path
import copy,gzip,hashlib,json,struct,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
from host_test import validate_artifacts,validate_tree,validate_config,NAME,HOST
from legacy_resources import parse_dtb
from android44_image import parse_newc
if len(sys.argv)!=3:raise SystemExit('Usage: test-host-diagnostic-profile.py KERNEL_DIR IMAGE_DIR')
p=Path(sys.argv[1]);out=Path(sys.argv[2]);validate_artifacts(p)
nodes=parse_dtb((p/(NAME+'.dtb')).read_bytes());resource=parse_dtb((p/'control-resources.dtb').read_bytes());smp=parse_dtb((p/'control-smp2.dtb').read_bytes())
mutations=[(HOST,'reg',struct.pack('>II',0x50000000,0x40000)),(HOST,'interrupts',struct.pack('>6I',0,67,4,0,65,4)),(HOST,'clocks',struct.pack('>II',1,24)),(HOST,'resets',struct.pack('>II',1,24)),(HOST,'clock-names',b'gr3d\0'),(HOST+'/gr3d@54180000','status',b'okay\0'),(HOST+'/dc@54200000','status',b'okay\0'),('/panel','status',b'okay\0'),('/nvmap/carveouts/generic@30000000','reg',struct.pack('>II',0x2e800000,0x11800000))]
for path,key,value in mutations:
    bad=copy.deepcopy(nodes);bad[path][key]=value
    try:validate_tree(bad,resource,smp)
    except AssertionError:pass
    else:raise AssertionError('Unsafe DT mutation accepted: '+path+'/'+key)
config=(p/'kernel.config').read_text()
for option in ['CPU_FREQ','SUSPEND','TEGRA_DC','TEGRA_HOST1X','TEGRA_IOVMM','TEGRA_AVP','TEGRA_RPC','NVMAP_ALLOW_SYSMEM','NVMAP_PAGE_POOLS','TEGRA_NVMAP_WINGRAY_RESOURCES']:
    lines=[l for l in config.splitlines() if not l.startswith('CONFIG_'+option+'=') and l!='# CONFIG_'+option+' is not set']
    lines.append('CONFIG_'+option+'=y')
    try:validate_config('\n'.join(lines))
    except AssertionError:pass
    else:raise AssertionError('Unsafe config mutation accepted: '+option)
image=(out/'wingray-host-diagnostic.img').read_bytes();manifest=json.loads((out/'host-manifest.json').read_text())
assert image[:8]==b'ANDROID!' and hashlib.sha256(image).hexdigest()==manifest['sha256']
ks,ka,rs,ra,ss,sa,tags,page=struct.unpack_from('<8I',image,8)
assert (ka,ra,ss,tags,page)==(0x10008000,0x11000000,0,0x10000100,2048)
k=image[page:page+ks];at=page+(ks+page-1)//page*page;r=image[at:at+rs]
assert k==(p/'zImage-dtb').read_bytes() and r==(out/'host-ramdisk.cpio.gz').read_bytes()
h=hashlib.sha1()
for data in (k,r,b''):h.update(data);h.update(struct.pack('<I',len(data)))
assert image[576:596]==h.digest() and len(image)<8*1024*1024 and ks<ra-ka
entries=parse_newc(gzip.decompress(r))
assert entries['bin/host-test-report'].data==(root/'diagnostic/host-test-report.sh').read_bytes()
assert entries['init'].data==(root/'diagnostic/init.sh').read_bytes()
assert not any(name.startswith('system/lib/') or name.startswith('bin/display-') or name=='system/bin/init' for name in entries)
assert b'/bin/host-test-report' in entries['bin/diagnostic-report'].data
assert manifest['physical_execution'] is False and not manifest['storage_mounts']
print('PASS host diagnostic: 19 unsafe DT/config mutations rejected; exact appended DTB, header/load addresses, payloads, SHA1/SHA256 and standalone RAM reporter verified.')
