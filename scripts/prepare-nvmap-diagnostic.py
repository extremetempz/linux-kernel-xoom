#!/usr/bin/env python3
"""Package isolated Motorola nvmap probe. No device actions or block writes."""
import argparse,gzip,hashlib,json,stat,struct,subprocess,sys
from pathlib import Path
from android44_image import Entry,parse_newc,pack_newc
from legacy_resources import validate_artifacts
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cached-sharing',action='store_true',help='Use the bounded two-client cacheable-buffer probe; original uncached source retained')
p.add_argument('--kernel-dir',type=Path,required=True)
p.add_argument('--build-root',type=Path,required=True)
p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args();out=a.output_dir.resolve();kernel=a.kernel_dir.resolve();build=a.build_root.resolve()
assert not out.exists() and out.is_relative_to(root/'artifacts')
validate_artifacts(kernel)
probe_source='diagnostic/nvmap-cached-sharing-probe.c' if a.cached_sharing else 'diagnostic/nvmap-allocator-probe.c'
if a.cached_sharing:
 assert '#define NVMAP_HANDLE_CACHEABLE       (0x3ul << 0)' in (root/'sources/kernel-donor/drivers/staging/tegra/include/linux/nvmap.h').read_text()
subprocess.run(['make','-s','-C',str(build/'source'),'O='+str(build/'out'),'ARCH=arm','INSTALL_HDR_PATH='+str(build/'headers'),'headers_install'],check=True)
# Generic builder is retained unchanged; only this opt-in wrapper adds allocator operations.
subprocess.run([sys.executable,str(root/'scripts/prepare-diagnostic.py'),'--kernel-dir',str(kernel),'--output-dir',str(out)],check=True)
probe=out/'nvmap-allocator-probe'
subprocess.run([str(root/'toolchains/android-gcc49/bin/arm-linux-androideabi-gcc'),'-Os','-Wall','-Wextra','-Werror','-nostdlib','-static','-fno-builtin','-fno-stack-protector','-fomit-frame-pointer','-marm','-march=armv7-a','-mfloat-abi=soft','-Wl,--build-id=none','-isystem',str(build/'headers/include'),'-I',str(root/'sources/kernel-donor/drivers/staging/tegra/video/nvmap'),str(root/probe_source),'-o',str(probe)],check=True)
elf=probe.read_bytes()
assert elf[:7]==b'\x7fELF\x01\x01\x01' and elf[18:20]==b'\x28\0'
assert not subprocess.check_output(['nm','-u',str(probe)]).strip()
assert b'INTERP' not in subprocess.check_output(['readelf','-lW',str(probe)])
assert b'Tag_Advanced_SIMD_arch:' not in subprocess.check_output(['readelf','-A',str(probe)])
entries=parse_newc(gzip.decompress((out/'ramdisk.cpio.gz').read_bytes()))
init=entries['init'];report=entries['bin/diagnostic-report']
anchor=b'# No unsolicited output:'
assert init.data.count(anchor)==1
entries['init']=Entry('init',init.mode,init.data.replace(anchor,b'/bin/busybox sh /bin/nvmap-resource-start > /run/nvmap-allocator-result.txt 2>&1 &\n'+anchor))
anchor=b"/bin/busybox printf 'XOOM_DMESG_BEGIN"
assert report.data.count(anchor)==1
entries[report.name]=Entry(report.name,report.mode,report.data.replace(anchor,b'/bin/busybox sh /bin/nvmap-resource-report\n'+anchor))
entries['bin/nvmap-allocator-probe']=Entry('bin/nvmap-allocator-probe',stat.S_IFREG|0o755,elf)
for name in ['nvmap-resource-start','nvmap-resource-report']:
 entries['bin/'+name]=Entry('bin/'+name,stat.S_IFREG|0o755,(root/('diagnostic/'+name+'.sh')).read_bytes())
ramdisk=gzip.compress(pack_newc(entries),mtime=0)
# Save generic pre-extension evidence; no preserved artifact is overwritten.
(out/'wingray-diagnostic.img').rename(out/'base-diagnostic.img')
(out/'ramdisk.cpio.gz').rename(out/'base-ramdisk.cpio.gz')
header=bytearray((out/'base-diagnostic.img').read_bytes()[:2048]);k=(kernel/'zImage-dtb').read_bytes()
struct.pack_into('<I',header,16,len(ramdisk))
h=hashlib.sha1()
for data in (k,ramdisk,b''):h.update(data);h.update(struct.pack('<I',len(data)))
header[576:596]=h.digest()
image=bytes(header)+k+b'\0'*(-len(k)%2048)+ramdisk+b'\0'*(-len(ramdisk)%2048)
assert len(image)<8*1024*1024
(out/'wingray-nvmap-diagnostic.img').write_bytes(image)
(out/'nvmap-ramdisk.cpio.gz').write_bytes(ramdisk)
manifest={'purpose':('CPU-only cacheable two-client sharing/lifetime smoke' if a.cached_sharing else 'CPU-only uncached generic allocator smoke')+'; no Android/GPU/IRAM/GART/DC/DVFS','sha256':hashlib.sha256(image).hexdigest(),'kernel_sha256':hashlib.sha256(k).hexdigest(),'probe_sha256':hashlib.sha256(elf).hexdigest(),'sources_sha256':{x:hashlib.sha256((root/x).read_bytes()).hexdigest() for x in [probe_source,'diagnostic/nvmap-resource-start.sh','diagnostic/nvmap-resource-report.sh','scripts/prepare-nvmap-diagnostic.py']},'storage_mounts':[],'physical_execution':False}
(out/'nvmap-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Allocator diagnostic ready; physical test pending:',out/'wingray-nvmap-diagnostic.img')
