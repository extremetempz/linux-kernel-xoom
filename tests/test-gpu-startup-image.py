#!/usr/bin/env python3
"""Verify startup-only image contents and unchanged tested hardware description."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,struct,subprocess,sys
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
from android44_image import parse_newc,boot_image
from gpu_test import validate_artifacts
spec=importlib.util.spec_from_file_location('pack',r/'scripts/prepare-gpu-render-diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=(49,50,51,52,53,54),type=int,default=54);a=parser.parse_args()
cookie=int('584d00'+str(a.attempt),16)
p=r/f'artifacts/gpu-startup{a.attempt}-ready';k=r/f'artifacts/gpu-startup{a.attempt}-kernel';validate_artifacts(k,startup_trace=True,trace_cookie=cookie)
manifest=json.loads((p/'manifest.json').read_text());image=(p/'wingray-gpu-render-diagnostic.img').read_bytes();ram=(p/'ramdisk.cpio.gz').read_bytes();e=parse_newc(gzip.decompress(ram))
assert manifest['startup_trace_only'] and manifest['trace_cookie']==hex(cookie)
assert not manifest['probe_timeout_seconds'] and not manifest['storage_mounts']
assert manifest['services']==['ueventd','gpu-startup']
assert hashlib.sha256(image).hexdigest()==manifest['sha256']
control=boot_image((k/'zImage-dtb').read_bytes(),ram)
address=int(manifest.get('ramdisk_load_address','0x11000000'),16)
assert address in (0x11000000,0x12000000)
if address!=0x11000000:
 assert a.attempt==53 and address+len(ram)<0x1fe00000
 expected=bytearray(control);struct.pack_into('<I',expected,20,address)
 assert image==bytes(expected) and image[:20]==control[:20] and image[24:]==control[24:]
else: assert image==control
if manifest.get('builtin_runtime'):
 assert a.attempt==54 and e=={} and manifest['ramdisk_uncompressed_size']==124
 builtin=gzip.decompress((k/'builtin-initramfs.cpio.gz').read_bytes())
 assert hashlib.sha256(builtin).hexdigest()==manifest['runtime_archive_sha256']
 e=parse_newc(builtin)
assert e==m.entries(m.runtime_files(),startup_trace=True)
assert 'bin/gpu-render-start' not in e
assert b'gpu-probe' not in e['init.rc'].data
assert b'/bin/gpu-startup-check' in e['init.rc'].data
for name in ('init','bin/gpu-startup-check','init.rc','bin/usb-report-loop','bin/diagnostic-server'):
 data=e[name].data
 assert not any(token in data for token in (b'LD_PRELOAD',b'XOOM_EGL_PROBE_CHILD',b'/dev/block/',b'mount_all')),name
assert b'RENDER_SKIPPED_STARTUP_TRACE' in e['bin/gpu-startup-check'].data
assert b'printf "1\\n"' in e['init'].data and b'printf "2\\n"' in e['init'].data
assert b'printf "A\\n"' in e['bin/usb-report-loop'].data and b'printf "B\\n"' in e['bin/usb-report-loop'].data
assert b'printf "C\\n"' in e['bin/diagnostic-server'].data
for n in ('init','bin/gpu-startup-check','bin/usb-report-loop','bin/diagnostic-server'):
 subprocess.run(['/bin/busybox','sh','-n'],input=e[n].data,check=True)
for name,sha in manifest['source_sha256'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==sha,name
assert (k/'tegra20-motorola-wingray-gpu-test.dtb').read_bytes()==(r/'artifacts/gpu-render48-v2-kernel/tegra20-motorola-wingray-gpu-test.dtb').read_bytes()
print('PASS startup-only image: exact payload/header/hash, fixed trace markers, no rendering invocation or block mounts, unchanged image-48 DT')
