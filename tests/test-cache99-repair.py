#!/usr/bin/env python3
"""Execute transaction control flow with fake commands/metadata, no devices."""
from pathlib import Path
import os,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
FAKE=r'''#!/usr/bin/python3
import os,sys,pathlib,subprocess
p=pathlib.Path(__file__).parent;name=pathlib.Path(sys.argv[0]).name;a=sys.argv[1:]
if name=='bb':name=a.pop(0)
with (p/'actions').open('a') as f:f.write(name+' '+' '.join(a)+'\n')
if name=='timeout':os.execv(str(p/'bb'),[str(p/'bb'),*a[4:]])
if name=='sync':sys.exit(1 if (p/'syncfail').exists() else 0)
if name=='cat':
 target=a[0]
 print((p/'ro').read_text().strip() if '/mmcblk0p9/' in target else '1');sys.exit(0)
if name=='touch':pathlib.Path(a[0]).touch();sys.exit(0)
if name=='preflight':sys.exit(1 if (p/'preflightfail').exists() else 0)
if name=='release':
 (p/'ro').write_text('0');sys.exit(1 if (p/'releasefail').exists() else 0)
if name=='lock':
 if (p/'lockfail').exists():sys.exit(1)
 (p/'ro').write_text('1');sys.exit(0)
if name=='checker':
 if '-n' in a:sys.exit(4 if (p/'checkfail').exists() else 0)
 sys.exit(4 if (p/'repairfail').exists() else 1)
if name=='sha256sum':print('fixturehash device');sys.exit(0)
raise SystemExit('unexpected '+name)
'''
def run(flag=None):
 with tempfile.TemporaryDirectory() as d:
  p=Path(d);(p/'ro').write_text('1')
  if flag:(p/flag).touch()
  for n in ('bb','preflight','release','lock','checker'):
   (p/n).write_text(FAKE);(p/n).chmod(0o755)
  s=(R/'diagnostic/cache99-repair.sh').read_text().replace('exec </dev/ttyGS0 >/dev/ttyGS0 2>&1','')
  for a,b in {'/bin/busybox':str(p/'bb'),'/bin/cache99-preflight':str(p/'preflight'),'/bin/cache99-release':str(p/'release'),'/bin/cache99-lock':str(p/'lock'),'/run/e2fsck':str(p/'checker'),'/run/cache99-attempted':str(p/'attempted')}.items():s=s.replace(a,b)
  r=subprocess.run(['/usr/bin/busybox','sh','-c',s],capture_output=True,text=True)
  return r,(p/'ro').read_text(),(p/'actions').read_text()
r,ro,a=run();assert r.returncode==0 and ro=='1' and 'COMPLETE_REQUIRES' in r.stdout
for flag in ('preflightfail','releasefail','repairfail','syncfail','lockfail','checkfail'):
 r,ro,a=run(flag);assert r.returncode!=0 and 'COMPLETE_REQUIRES' not in r.stdout,(flag,r)
 if flag!='lockfail':assert ro=='1'
 if flag=='preflightfail':assert 'release ' not in a
 else:assert 'lock ' in a
print('PASS actual repair shell: preflight first, uncertain release cleanup, repair/sync/relock/check failure gates')
