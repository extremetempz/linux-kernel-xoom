#!/usr/bin/env python3
"""Verify startup-only image contents and unchanged tested hardware description."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,subprocess,sys
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
from android44_image import parse_newc,boot_image
from gpu_test import validate_artifacts
spec=importlib.util.spec_from_file_location('pack',r/'scripts/prepare-gpu-render-diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=r/'artifacts/gpu-startup50-ready';k=r/'artifacts/gpu-startup50-kernel';validate_artifacts(k,startup_trace=True,trace_cookie=0x584d0050)
manifest=json.loads((p/'manifest.json').read_text());image=(p/'wingray-gpu-render-diagnostic.img').read_bytes();ram=(p/'ramdisk.cpio.gz').read_bytes();e=parse_newc(gzip.decompress(ram))
assert manifest['startup_trace_only'] and manifest['trace_cookie']=='0x584d0050'
assert not manifest['probe_timeout_seconds'] and not manifest['storage_mounts']
assert manifest['services']==['ueventd','gpu-startup']
assert hashlib.sha256(image).hexdigest()==manifest['sha256']
assert image==boot_image((k/'zImage-dtb').read_bytes(),ram)
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
