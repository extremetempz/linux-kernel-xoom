#!/usr/bin/env python3
"""Prepare a separate RAM-only NVIDIA Android runtime; never flashes or mounts."""
from pathlib import Path
import argparse,dataclasses,gzip,hashlib,json,re,stat,subprocess,sys
from android44_image import Entry,original_entries,ramdisk_entries,pack_newc,boot_image,digest,BUSYBOX_SHA256
from prepare_android_gpu_inputs import graphics_hashes
# Reuse the already checked static-runtime/ROM-reference gates.
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('android_pack',ROOT/'scripts/prepare-android44.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
RELEASE='4.4.147-wingray-android44-gpu'

def entries(runtime):
 config=(runtime/'kernel.config').read_bytes()
 for line in (b'CONFIG_LOCALVERSION="-wingray-android44-gpu"\n',b'CONFIG_ANDROID_BINDER_IPC_32BIT=y\n',b'CONFIG_FB_TEGRA_WINGRAY_LEGACY=y\n',b'CONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST=y\n'):
  assert line in config,line
 original=original_entries((ROOT/'artifacts/hardware-private/backup-boot.img').read_bytes())
 busybox=base.check_static_arm(ROOT/'artifacts/busybox-static-armv5l','v5T');assert digest(busybox)==BUSYBOX_SHA256
 hashes,refs=base.system_hashes();gpu=graphics_hashes()
 hashes+=b''.join((sha+'  '+name+'\n').encode() for name,sha in sorted(gpu.items()))
 files={'bin/busybox':busybox,'bin/android44-system-sha256':hashes}
 for name,source in [('android44-abi-probe','android44-abi-probe.c'),('touch-events','touch-events.c'),('cpu-handoff-probe','cpu-handoff-probe.c')]:
  files['bin/'+name]=base.checked_runtime(runtime,name,ROOT/'diagnostic'/source,RELEASE,config)
 assert json.loads((runtime/'display-pattern-manifest.json').read_text())['legacy_wingray_layout']
 files['bin/display-pattern']=base.checked_runtime(runtime,'display-pattern',ROOT/'diagnostic/display-pattern.c')
 helpers={'init':'android44-init.sh','bin/android44-bootstrap':'android44-gpu-bootstrap.sh',
  'bin/android-service-runner':'android-service-runner.sh','bin/usb-report-loop':'usb-report-loop.sh',
  'bin/diagnostic-server':'server.sh','bin/diagnostic-report':'report.sh','bin/android44-report':'android44-gpu-report.sh',
  'bin/display-report':'display-report.sh','bin/touch-report':'touch-report.sh','bin/soc-report':'soc-report.sh'}
 for name,source in helpers.items():
  path=ROOT/'diagnostic'/source;subprocess.run(['bash','-n',str(path)],check=True);files[name]=path.read_bytes()
 result=ramdisk_entries(original,files)
 # Match the working original ROM's permissions only for the three GPU channels used.
 u=result['ueventd.stingray.rc'];perms=b'\n# Original Wingray NVIDIA channels; explicit paths, no block access.\n'+b''.join((name+' 0666 root root\n').encode() for name in ('/dev/nvhost-ctrl','/dev/nvhost-gr2d','/dev/nvhost-gr3d'))
 result[u.name]=dataclasses.replace(u,data=u.data+perms)
 # Keep the old experiment's board identity and RAM-data services; select vendor modules via tegra.
 assert b'ro.hardware=stingray\n' in result['default.prop'].data
 assert b'/system/lib/egl/libGLES_android.so /run/xoom-egl/' not in files['bin/android44-bootstrap']
 assert b'0 1 tegra' in files['bin/android44-bootstrap']
 assert not any(x in files['bin/android44-bootstrap'] for x in (b' gralloc.default ',b'libGLES_android.so /run/xoom-egl'))
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-dir',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
 assert not a.archive.exists();data=pack_newc(entries(a.runtime_dir));a.archive.write_bytes(data)
 print('Prepared combined RAM-only Android/NVIDIA archive:',len(data),'bytes; not a flashable image')
if __name__=='__main__':main()
