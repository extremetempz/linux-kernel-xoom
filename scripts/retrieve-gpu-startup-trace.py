#!/usr/bin/env python3
"""One guarded read-only snapshot using the already tested ARM trace reader.

Requires the original ROM restored and complete partition hashes verified.
Never flashes/reboots, never falls back to /dev/mem read(), never retries mmap.
Temporary reader lives in /dev RAM and is removed in finally.
"""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,json,re,subprocess,sys,uuid
ROOT=Path(__file__).resolve().parents[1]
READER_SHA='f6d45ea6e2b1269094599d9cdfe0ce8b8a55a23d4b6b382b7e44ddc0ff3633eb'
ORIGINAL={'boot':('mmcblk0p7',8388608,'64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588'),
          'recovery':('mmcblk0p6',12582912,'5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606')}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--serial',required=True);p.add_argument('--attempt-dir',type=Path,required=True)
 p.add_argument('--kernel-dir',type=Path,required=True);a=p.parse_args()
 out=a.attempt_dir.resolve();assert out.is_relative_to(ROOT/'artifacts') and out.is_dir()
 marker=out/'trace-mapping-attempted.txt';assert not marker.exists(),'Do not repeat a mapping attempt'
 from gpu_test import validate_artifacts,startup_cookie
 cookie=startup_cookie(a.kernel_dir)
 validate_artifacts(a.kernel_dir,startup_trace=True,trace_cookie=cookie)
 state=json.loads((out/'test-state-private.json').read_text())
 assert state.get('full_original_hashes_verified') and not state['original_restoration_pending']
 artifacts=json.loads((out/'kernel-artifact-verification.json').read_text())
 assert artifacts['compiled_outputs_match']
 assert artifacts['candidate_sha256']==state['candidate_sha256']
 assert hashlib.sha256((a.kernel_dir/'zImage-dtb').read_bytes()).hexdigest()==artifacts['kernel_sha256']
 assert hashlib.sha256((a.kernel_dir/'System.map').read_bytes()).hexdigest()==artifacts['system_map_sha256']
 def adb(*args):
  result=subprocess.run(['/usr/bin/adb','-s',a.serial,*args],capture_output=True,timeout=100)
  assert not result.returncode,(result.returncode,result.stderr)
  return result.stdout.replace(b'\r\n',b'\n')
 def shell(cmd):return adb('shell',cmd)
 def save(name,data):
  with (out/name).open('xb') as f:f.write(data)
 identity=shell('getprop ro.product.device; uname -r; id; getprop sys.boot_completed')
 assert b'wingray\n' in identity and b'2.6.39.4-ElementalX-Xoom-2.1+\n' in identity and b'uid=0(root)' in identity and identity.rstrip().endswith(b'1')
 bootid=shell('cat /proc/sys/kernel/random/boot_id')
 assert shell('printf abc | /system/xbin/busybox sha256sum').split()[0]==b'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
 for name,(part,size,sha) in ORIGINAL.items():
  assert int(shell(f'cat /sys/block/mmcblk0/{part}/size'))*512==size
  assert shell(f'/system/xbin/busybox sha256sum /dev/block/{part}').split()==[sha.encode(),f'/dev/block/{part}'.encode()]
 iomem=shell('cat /proc/iomem')
 for begin,end in re.findall(rb'^\s*([0-9a-f]+)-([0-9a-f]+)\s*:',iomem,re.M):
  assert int(end,16)<0x1fe00000 or int(begin,16)>0x1fe00fff,'Trace page has an owner in current iomem'
 assert b'1ff00000-1fffffff : ram_console' in iomem
 save('trace-preflight-iomem-private.txt',iomem)
 reader=ROOT/'artifacts/trace-reader/mmap-snapshot'
 assert hashlib.sha256(reader.read_bytes()).hexdigest()==READER_SHA
 before=shell('dmesg');save('trace-dmesg-before-private.txt',before)
 remote='/dev/xoom-startup49-'+uuid.uuid4().hex
 shell('mkdir '+remote)
 try:
  adb('push',str(reader),remote+'/reader')
  shell('chmod 500 '+remote+'/reader')
  assert shell('/system/xbin/busybox sha256sum '+remote+'/reader').split()[0]==READER_SHA.encode()
  save('trace-reader-default.txt',shell(remote+'/reader'))
  save('trace-mapping-attempted.txt',b'One PROT_READ mmap2 snapshot of the existing 0x1fe00000 trace page; no retries.\n')
  transport=shell('( '+remote+'/reader --read-reserved-trace; rc=$?; printf "\\nXOOM_MMAP_RC=%s\\n" "$rc" ) 2>&1 | /system/xbin/busybox base64')
  result=base64.b64decode(b''.join(transport.split()),validate=True)
  save('trace-reader-result-private.bin',result)
  assert len(result)==128+len(b'\nXOOM_MMAP_RC=0\n') and result[128:]==b'\nXOOM_MMAP_RC=0\n','Readback was not a successful stable 128-byte snapshot'
  save('startup-trace-private.bin',result[:128])
  after=shell('dmesg');save('trace-dmesg-after-private.txt',after)
  assert shell('cat /proc/sys/kernel/random/boot_id')==bootid
  assert shell('getprop sys.boot_completed').strip()==b'1'
  assert after.startswith(before) and not re.search(rb'(?i)(panic|BUG:|WARNING:|Unhandled fault|Oops:)',after[len(before):])
 finally:
  shell('rm '+remote+'/reader; rmdir '+remote)
  assert shell('if [ -e '+remote+' ]; then echo PRESENT; else echo REMOVED; fi').strip()==b'REMOVED'
  save('trace-reader-cleanup.txt',b'Temporary RAM reader removed.\n')
 # Decode only after cleanup. A stale record is retained privately and rejected.
 spec=importlib.util.spec_from_file_location('decode',ROOT/'scripts/decode-gpu-startup-trace.py')
 decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
 decoded=decoder.decode(result[:128],(a.kernel_dir/'System.map').read_text(),cookie=cookie)
 save('startup-trace-decoded.json',(json.dumps(decoded,indent=2)+'\n').encode())
 print(json.dumps(decoded,indent=2))

if __name__=='__main__':main()
