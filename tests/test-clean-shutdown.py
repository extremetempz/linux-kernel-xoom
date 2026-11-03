#!/usr/bin/env python3
"""Execute the real shutdown shell against fake commands and regular metadata files."""
from pathlib import Path
import os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from shutdown_profile import init_actions
rc=init_actions().decode()
assert 'class_stop late_start' in rc and 'class_stop main' in rc and 'class_stop core' in rc
assert 'powerctl shutdown' in rc and 'powerctl reboot' in rc
assert 'powerctl ${sys.powerctl}' not in rc and 'reboot,recovery' not in rc
FAKE=r'''#!/usr/bin/python3
import os,sys,pathlib,subprocess
root=pathlib.Path(__file__).parent
a=sys.argv[1:];cmd=a.pop(0)
with (root/'actions').open('a') as f:f.write(cmd+' '+' '.join(a)+'\n')
if cmd=='timeout':os.execv(sys.argv[0],[sys.argv[0],*a[4:]])
if cmd=='id':print('0');sys.exit(0)
if cmd=='mkdir':
 try:os.mkdir(a[0]);sys.exit(0)
 except FileExistsError:sys.exit(1)
if cmd=='sync':sys.exit(1 if (root/'fail-sync').exists() else 0)
if cmd=='setprop':sys.exit(0)
if cmd=='dd':
 skip=next(v for v in a if v.startswith('skip='))
 sys.stdout.buffer.write(b'\x00\x00' if ((root/'dirty').exists() or ((root/'dirty-cache').exists() and 'if=/dev/mmcblk0p9' in a)) else (b'\x01\x00' if skip=='skip=1082' else b'\x42'));sys.exit(0)
if cmd=='umount':
 if (root/'busy').exists() and a[0]=='/data':sys.exit(1)
 p=root/'mountinfo';lines=p.read_text().splitlines();p.write_text('\n'.join(l for l in lines if l.split()[4]!=a[0])+'\n');sys.exit(0)
if cmd=='mount':
 if (root/'fail-remount').exists():sys.exit(1)
 p=root/'mountinfo';lines=[]
 for l in p.read_text().splitlines():
  v=l.split()
  if v[4]==a[-1]:v[5]='ro';v[-1]='ro'
  lines.append(' '.join(v))
 p.write_text('\n'.join(lines)+'\n');sys.exit(0)
if cmd in ('awk','sort','od','tr'):sys.exit(subprocess.call(['/usr/bin/'+cmd,*a]))
raise SystemExit('unexpected fake command '+cmd)
'''
def test(flags=(),alias=False,cache=False,approved=False):
 with tempfile.TemporaryDirectory(prefix='xoom-shutdown-') as d:
  p=Path(d);fake=p/'bb';fake.write_text(FAKE);fake.chmod(0o755)
  (p/'marker').touch()
  if approved:(p/'cache-approved').touch()
  for flag in flags:(p/flag).touch()
  mounts='1 0 0:1 / / ro - rootfs rootfs ro\n2 1 179:10 / /data rw - ext4 /dev/mmcblk0p10 rw\n'
  mounts+='3 1 '+('179:9' if cache else '0:9')+' / /cache rw - '+('ext4 /dev/mmcblk0p9' if cache else 'tmpfs tmpfs')+' rw\n'
  if alias:mounts+='4 1 179:10 / /alias rw - ext4 /dev/mmcblk0p10 rw\n'
  (p/'mountinfo').write_text(mounts)
  source=(ROOT/'diagnostic/clean-shutdown.sh').read_text()
  for old,new in {'/bin/busybox':str(fake),'/run/android44-shutdown.txt':str(p/'trace'),
      '/run/xoom-shutdown.lock':str(p/'lock'),'/bin/clean-shutdown-enabled':str(p/'marker'),
      '/bin/storage-cache-approved':str(p/'cache-approved'),'/proc/self/mountinfo':str(p/'mountinfo'),
      '/dev/kmsg':str(p/'kmsg'),'/system/bin/setprop':str(fake)+' setprop'}.items():source=source.replace(old,new)
  result=subprocess.run(['/usr/bin/busybox','sh','-c',source,'test','shutdown'],capture_output=True)
  sent='setprop sys.xoom.shutdown_ready shutdown' in (p/'actions').read_text()
  return result.returncode,sent,(p/'trace').read_text()
assert test()[:2]==(0,True)
assert test(flags=('busy',))[:2]==(0,True)
for params in ({'flags':('fail-sync',)}, {'flags':('busy','fail-remount')},
               {'flags':('dirty',)}, {'alias':True}, {'cache':True}):
 code,sent,trace=test(**params);assert code!=0 and not sent,(params,trace)
assert test(cache=True,approved=True)[:2]==(0,True)
print('PASS: actual shutdown transaction, unmount/RO fallback, alias/dirty/sync failures block native handoff; no device I/O')

assert test(flags=('dirty-cache',),cache=True,approved=True)[:2]==(1,False)
