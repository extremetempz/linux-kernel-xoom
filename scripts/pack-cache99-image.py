#!/usr/bin/env python3
"""Audit and pack the built-in p9-only RAM repair image. Never flashes."""
from pathlib import Path
import argparse,hashlib,json,lzma,shutil,struct
from android44_image import pack_newc,parse_newc,boot_image
from legacy_resources import parse_dtb
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-root',type=Path,required=True);p.add_argument('--runtime-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
b=a.build_root/'out';out=a.output_dir
assert not out.exists()
config=(b/'.config').read_text()
assert 'CONFIG_USB_G_SERIAL=y\n' in config and '# CONFIG_USB_MASS_STORAGE is not set\n' in config
assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="tegra20-motorola-wingray-cache-repair99"\n' in config
runtime=(a.runtime_dir/'runtime.cpio').read_bytes();rm=json.loads((a.runtime_dir/'manifest.json').read_text())
assert sha(runtime)==rm['runtime_sha256']
assert lzma.decompress((b/'usr/initramfs_data.cpio.xz').read_bytes())==runtime
entries=parse_newc(runtime)
assert 'bin/storage-data-approved' not in entries and 'bin/storage-policy' not in entries
for name,h in rm['sources'].items():assert sha((ROOT/name).read_bytes())==h,name
for mode,h in rm['helpers'].items():assert sha(entries['bin/cache99-'+mode].data)==h
assert entries['bin/cache99-repair'].data==(ROOT/'diagnostic/cache99-repair.sh').read_bytes()
dts=b/'arch/arm/boot/dts';dt=(dts/'tegra20-motorola-wingray-cache-repair99.dtb').read_bytes()
base=parse_dtb((dts/'tegra20-motorola-wingray-android44-persistent.dtb').read_bytes());tree=parse_dtb(dt)
assert set(base)==set(tree)
for name in tree:
 before=dict(base[name]);after=dict(tree[name])
 if name=='/':
  before.pop('model');after.pop('model');assert after.pop('motorola,wingray-cache-repair99')==b''
 if name=='/sdhci@c8000600':assert after.pop('motorola,xoom-cache-repair-only')==b''
 assert before==after,name
kernel=(b/'arch/arm/boot/zImage').read_bytes();combined=(b/'arch/arm/boot/zImage-dtb').read_bytes()
assert combined==kernel+dt and struct.unpack_from('<I',kernel,36)[0]==0x016f2818
for name in ('block/blk-core.c','drivers/mmc/card/block.c','include/linux/genhd.h'):
 assert (a.build_root/'source'/name).read_bytes()==(ROOT/'sources/kernel-donor'/name).read_bytes()
ram=lzma.compress(pack_newc({}),format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32)
image=boot_image(combined,ram);assert len(image)<8388608
out.mkdir(mode=0o700);(out/'wingray-cache99-offline-repair.img').write_bytes(image)
shutil.copyfile(b/'.config',out/'kernel.config');(out/'runtime.cpio').write_bytes(runtime)
manifest={'image':'wingray-cache99-offline-repair.img','sha256':sha(image),'bytes':len(image),
 'builtin_runtime_sha256':sha(runtime),'kernel_sha256':sha(combined),'checker_sha256':rm['checker_sha256'],
 'kernel_config_sha256':sha(config.encode()),'dt_sha256':sha(dt),
 'startup':'RAM-only checker fixture tests; all media initially RO','target':'fixed p9 only',
 'other_partitions':'kernel denies writes even if their RO flag is cleared','discard':'denied',
 'repair_command':'PREFLIGHT_P9 then REPAIR_P9 and matching REPAIR_P9_CONFIRM',
 'automatic_physical_repair':False,'hardware_validated':False,'flash_executed':False,
 'requires_source_sha256':'7053be21ae7e7c627aa829eafc97501cd5ceae2063f56177a4ce28488b3e4aef',
 'source_hashes':rm['sources'],'helper_hashes':rm['helpers']}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
