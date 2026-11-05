#!/usr/bin/env python3
"""Execute actual shutdown shell against host fixtures; never accesses a device."""
from pathlib import Path
import subprocess,sys,tempfile
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from shutdown_profile import init_actions
rc=init_actions().decode()
assert all('class_stop '+n in rc for n in ('late_start','main','core'))
assert 'powerctl shutdown' in rc and 'powerctl reboot' in rc
assert '/cache/' not in rc and '/data/' not in rc
assert 'powerctl ${sys.powerctl}' not in rc and 'reboot,recovery' not in rc
FAKE=r'''#!/usr/bin/python3
import os,sys,pathlib,time
root=pathlib.Path(__file__).parent;a=sys.argv[1:];cmd=a.pop(0)
with (root/'actions').open('a') as f:f.write(cmd+' '+' '.join(a)+'\n')
if cmd=='id':print('0');sys.exit(0)
if cmd=='sleep':time.sleep(.02);sys.exit(0)
if cmd=='sync':sys.exit(1 if (root/'fail-sync').exists() else 0)
if cmd=='dd':
 skip=next(x for x in a if x.startswith('skip='))
 cache='if=/dev/mmcblk0p9' in a
 if skip=='skip=1082':v=b'\0\0' if (root/'dirty').exists() else b'\1\0'
 elif skip=='skip=1120':v=b'\x46' if (root/'recovery').exists() or (cache and (root/'dirty-cache').exists()) else b'\x42'
 elif skip=='skip=1428':v=b'\1\0\0\0' if (root/'errors').exists() else b'\0'*4
 else:raise SystemExit('unexpected offset')
 sys.stdout.buffer.write(v);sys.exit(0)
if cmd=='mount':
 if '--make-private' in a:sys.exit(1 if (root/'private-fail').exists() else 0)
 assert a[:4]==['-t','ext4','-o','remount,ro,nosuid,nodev,noatime']
 assert a[-2] in ('/dev/mmcblk0p9','/dev/mmcblk0p10')
 if (root/'hang-mount').exists():time.sleep(20)
 if (root/'fail-remount').exists():sys.exit(1)
 p=root/'mountinfo';lines=[]
 for l in p.read_text().splitlines():
  v=l.split()
  if v[4]==a[-1]:v[5]='ro,nosuid,nodev';v[-1]='ro'
  if (root/'vfs-only').exists():v[-1]='rw'
  lines.append(' '.join(v))
 p.write_text('\n'.join(lines)+'\n');sys.exit(0)
if cmd=='setprop':sys.exit(1 if (root/'fail-setprop').exists() else 0)
if cmd=='umount':raise SystemExit('physical unmount must never be called')
os.execv('/usr/bin/busybox',['/usr/bin/busybox',cmd,*a])
'''
def run(flags=(),cache=True,approved=True,alias=False,wrong=False,mode='shutdown'):
 with tempfile.TemporaryDirectory(prefix='xoom-shutdown1105-') as d:
  p=Path(d);bb=p/'bb';bb.write_text(FAKE);bb.chmod(0o755);(p/'enabled').touch()
  for n in flags:(p/n).touch()
  if approved:(p/'approved').touch()
  text='1 0 0:1 / / ro - rootfs rootfs ro\n2 1 '+('179:9' if wrong else '179:10')+' / /data rw,nosuid,nodev - ext4 /dev/mmcblk0p10 rw\n'
  text+='3 1 '+('179:9' if cache else '0:9')+' / /cache rw,nosuid,nodev - '+('ext4 /dev/mmcblk0p9' if cache else 'tmpfs tmpfs')+' rw\n'
  if alias:text+='4 1 179:10 / /alias rw - ext4 /dev/mmcblk0p10 rw\n'
  (p/'mountinfo').write_text(text)
  source=(R/'diagnostic/clean-shutdown.sh').read_text()
  for a,b in {'/bin/busybox':str(bb),'/run/':str(p)+'/', '/bin/clean-shutdown-enabled':str(p/'enabled'),'/bin/storage-cache-approved':str(p/'approved'),'/proc/self/mountinfo':str(p/'mountinfo'),'/dev/kmsg':str(p/'kmsg'),'/proc/sysrq-trigger':str(p/'absent-sysrq'),'/system/bin/setprop':str(bb)+' setprop'}.items():source=source.replace(a,b)
  result=subprocess.run(['/usr/bin/busybox','sh','-c',source,'fixture',mode],capture_output=True,timeout=15)
  actions=(p/'actions').read_text() if (p/'actions').exists() else ''
  trace=(p/'android44-shutdown.txt').read_text() if (p/'android44-shutdown.txt').exists() else ''
  sent='setprop sys.xoom.shutdown_ready '+mode in actions
  assert 'umount /cache' not in actions and 'umount /data' not in actions
  assert 'timeout ' not in actions
  return result.returncode,sent,trace,actions
for params in ({},{'cache':False,'approved':False},{'mode':'reboot'}):
 code,sent,trace,actions=run(**params);assert code==0 and sent,(trace,actions)
for params in ({'flags':('fail-sync',)},{'flags':('fail-remount',)},{'flags':('dirty',)},
               {'flags':('recovery',)},{'flags':('dirty-cache',)},{'flags':('errors',)},
               {'flags':('vfs-only',)},{'flags':('private-fail',)},{'flags':('fail-setprop',)},
               {'alias':True},{'wrong':True},{'approved':False},{'cache':False,'approved':True}):
 code,sent,trace,actions=run(**params)
 assert code!=0,(params,trace)
 if params.get('flags')!=('fail-setprop',):assert not sent,(params,trace)
code,sent,trace,actions=run(flags=('hang-mount',))
assert code!=0 and not sent and 'STALLED_cache_readonly' in trace,trace
assert run(mode='reboot,recovery')[:2]==(1,False)
print('PASS actual shutdown: RO-remount first, no physical unmount/log writes, bounded nonblocking failure, clean-state/alias/identity gates and fixed native handoff')
