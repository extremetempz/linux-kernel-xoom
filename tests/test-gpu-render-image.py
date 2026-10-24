#!/usr/bin/env python3
"""Verify the packed RAM-only image and original runtime dependency closure."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,re,struct,sys,subprocess
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
from android44_image import parse_newc,boot_image
from gpu_test import validate_artifacts
spec=importlib.util.spec_from_file_location('gpu_pack',r/'scripts/prepare-gpu-render-diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=(48,55,56),type=int,default=56);a=parser.parse_args()
label='gpu-render48-v2' if a.attempt==48 else f'gpu-render{a.attempt}'
k=r/f'artifacts/{label}-kernel';p=r/f'artifacts/{label}-ready'
validate_artifacts(k,startup_trace=a.attempt in (55,56),trace_cookie=0x584d0000+int(str(a.attempt),16) if a.attempt in (55,56) else 0x584d0049)
image=(p/'wingray-gpu-render-diagnostic.img').read_bytes();ram=(p/'ramdisk.cpio.gz').read_bytes();manifest=json.loads((p/'manifest.json').read_text())
assert hashlib.sha256(image).hexdigest()==manifest['sha256']
assert image==boot_image((k/'zImage-dtb').read_bytes(),ram)
assert len(image)<8*1024*1024
entries=parse_newc(gzip.decompress(ram));files=m.runtime_files()
if a.attempt in (55,56):
 assert manifest['builtin_runtime'] and manifest['rendering_enabled'] and not manifest['startup_trace_only']
 assert manifest['retained_startup_trace'] and manifest['probe_timeout_seconds']==35
 assert manifest['services']==['ueventd','gpu-probe'] and not manifest['storage_mounts']
 assert entries=={} and manifest['ramdisk_uncompressed_size']==124
 data=gzip.decompress((k/'builtin-initramfs.cpio.gz').read_bytes())
 assert hashlib.sha256(data).hexdigest()==manifest['runtime_archive_sha256']
 entries=parse_newc(data)
 assert entries==m.entries(files,startup_trace=True,render_probe=True,deferred_probe=a.attempt==56)
else: assert entries==m.entries(files)
assert entries['sbin/ueventd'].data==b'/init.android'
assert b'exec /init.android' in entries['init'].data
assert entries['init.rc'].data.count(b'service ')==2
assert b'start gpu-probe' in entries['init.rc'].data and b'oneshot' in entries['init.rc'].data
assert b'LD_PRELOAD' not in entries['init'].data+entries['init.rc'].data
script=entries['bin/gpu-render-start'].data
assert b'timeout -s KILL 35 /bin/busybox env XOOM_EGL_PROBE_CHILD=1 LD_PRELOAD=' in script
assert b'> /run/gpu-probe-output.txt 2>&1' in script
for name,data in entries.items():
 if name in ('init','init.rc') or name.startswith('bin/') and data.data.startswith(b'#!'):
  assert b'/dev/block/' not in data.data and b'mount_all' not in data.data,name
for name,path in files.items():
 assert entries[name].data==path.read_bytes()
 for needed in re.findall(r'Shared library: \[([^\]]+)\]',subprocess.check_output(['readelf','-dW',str(path)],text=True)):
  assert 'system/lib/'+needed in entries,needed
for name,expected in manifest['source_sha256'].items():
 assert hashlib.sha256((r/name).read_bytes()).hexdigest()==expected,name
assert not any(n.startswith('fstab') or 'GLES_android' in n for n in entries)
print('PASS image header/digest/payload, RAM-only services, child-only preload, timeout, ARM runtime dependency closure and pinned inputs; no hardware verdict')

if a.attempt==56:
 assert manifest['deferred_probe'] and manifest['trace_cookie']=='0x584d0056'
 script=entries['bin/gpu-render-start'].data;server=entries['bin/diagnostic-server'].data
 assert script.index(b'XOOM_GPU_RENDER_WAIT_USB_GATE')<script.index(b'/bin/busybox timeout -s KILL 35 ')
 assert b'GPU_RUN' in server and b'/run/gpu-probe-release' in server
 assert b'gate_wait" -ge 300' in script and b'set -C' in server
 print('PASS deferred probe gate retained in packed runtime; release is separate from PING/REPORT')
