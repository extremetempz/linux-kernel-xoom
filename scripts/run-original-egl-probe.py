#!/usr/bin/env python3
"""Run the EGL probe in one disposable child on the original ROM, never flash.

Temporary module goes only into /dev tmpfs. Installed graphics settings, Android
services, boot/recovery and on-disk library files are never modified by this tool.
Vendor code executes its ordinary EGL initialization/drawing/cleanup routines.
"""
import argparse,hashlib,json,re,shlex,subprocess,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--module-dir',type=Path,required=True)
p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args();source=a.module_dir.resolve();out=a.output_dir.resolve()
assert source.is_relative_to(root/'artifacts') and out.is_relative_to(root/'artifacts') and not out.exists()
module=source/'xoom-egl-probe.so';manifest=json.loads((source/'manifest.json').read_text())
assert hashlib.sha256(module.read_bytes()).hexdigest()==manifest['module_sha256']
for name,digest in manifest['sources'].items():assert hashlib.sha256((root/'diagnostic/egl-probe'/name).read_bytes()).hexdigest()==digest
serial=json.loads((root/'artifacts/trace-boot-attempt-19-prepared/device-private.json').read_text())['serial']
adb=['/usr/bin/adb','-s',serial]
def call(*args,timeout=20):
 r=subprocess.run([*adb,*args],capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError('ADB operation failed: '+r.stderr.decode(errors='replace'))
 return r.stdout.replace(b'\r\n',b'\n')
def shell(text,timeout=20):return call('shell',text,timeout=timeout)
identity=shell('uname -r; getprop ro.product.device; getprop sys.boot_completed; id')
assert b'2.6.39.4-ElementalX-Xoom-2.1+' in identity and b'wingray' in identity and b'\n1\n' in identity and b'uid=0(root)' in identity
mounts=shell('cat /proc/mounts');assert re.search(rb'^tmpfs /dev tmpfs ',mounts,re.M)
bootid=shell('cat /proc/sys/kernel/random/boot_id')
assert shell('printf abc | /system/xbin/busybox sha256sum').split()[0]==b'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
# Match installed wrappers and NVIDIA renderer, not an unrelated donor blob set.
libs=['libEGL.so','libGLESv2.so','libc.so','egl/libEGL_tegra.so','egl/libGLESv2_tegra.so']
for name in libs:
 expected=hashlib.sha256((root/'artifacts/hardware-private/system-lib'/name).read_bytes()).hexdigest()
 value=shell('/system/xbin/busybox sha256sum '+shlex.quote('/system/lib/'+name)).split()
 assert value and value[0].decode()==expected,'Installed library differs: '+name
out.mkdir();(out/'identity-private.txt').write_bytes(identity)
remote='/dev/xoom-egl-probe41';created=False
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'module_sha256':manifest['module_sha256'],'original_rom_only':True,'flash_performed':False,'new_kernel_acceleration_proven':False,'state':'started'}
try:
 ready=shell('if [ -e '+remote+' ]; then echo EXISTS; else mkdir '+remote+' && chmod 700 '+remote+' && echo CREATED; fi')
 assert ready.strip()==b'CREATED','Refuse to overwrite a pre-existing remote directory'
 created=True
 call('push',str(module),remote+'/xoom-egl-probe.so')
 assert shell('/system/xbin/busybox sha256sum '+remote+'/xoom-egl-probe.so').split()[0].decode()==manifest['module_sha256']
 # Environment applies only to the new child. Do not export into a service.
 output=shell('XOOM_EGL_PROBE_CHILD=1 LD_PRELOAD='+remote+'/xoom-egl-probe.so /system/bin/sh -c :; rc=$?; printf "\\nXOOM_EGL_CHILD_STATUS %s\\n" "$rc"',timeout=35)
 (out/'probe-output-private.txt').write_bytes(output)
 passed=(b'XOOM_EGL_ISOLATED_CHILD_BEGIN' in output and b'XOOM_EGL_OFFSCREEN_READBACK_PASS' in output and b'frame=0 triangle_and_background_readback=pass' in output and b'frame=1 triangle_and_background_readback=pass' in output and b'XOOM_EGL_CHILD_STATUS 0' in output and b'XOOM_EGL_PROBE_FAILED' not in output)
 result.update(state='passed' if passed else 'failed',output_sha256=hashlib.sha256(output).hexdigest())
 print(output.decode(errors='replace'))
finally:
 if created:
  cleaned=shell('rm '+remote+'/xoom-egl-probe.so; rmdir '+remote+'; if [ ! -e '+remote+' ]; then echo REMOVED; fi')
  result['temporary_ram_module_removed']=cleaned.strip()==b'REMOVED'
  assert result['temporary_ram_module_removed']
 result['same_original_boot_id']=shell('cat /proc/sys/kernel/random/boot_id')==bootid
 result['original_android_boot_complete']=shell('getprop sys.boot_completed').strip()==b'1'
 (out/'result-private.json').write_text(json.dumps(result,indent=2)+'\n')
print('Original-ROM probe result:',result['state'],'; no new-kernel acceleration claim; no flash.')
