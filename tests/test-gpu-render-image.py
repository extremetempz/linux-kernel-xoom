#!/usr/bin/env python3
"""Verify the packed RAM-only image and original runtime dependency closure."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,struct,sys,subprocess
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
from android44_image import parse_newc,boot_image
from gpu_test import validate_artifacts
spec=importlib.util.spec_from_file_location('gpu_pack',r/'scripts/prepare-gpu-render-diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
k=r/'artifacts/gpu-render48-v2-kernel';p=r/'artifacts/gpu-render48-v2-ready';validate_artifacts(k)
image=(p/'wingray-gpu-render-diagnostic.img').read_bytes();ram=(p/'ramdisk.cpio.gz').read_bytes();manifest=json.loads((p/'manifest.json').read_text())
assert hashlib.sha256(image).hexdigest()==manifest['sha256']
assert image==boot_image((k/'zImage-dtb').read_bytes(),ram)
assert len(image)<8*1024*1024
entries=parse_newc(gzip.decompress(ram));files=m.runtime_files()
assert entries==m.entries(files)
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
