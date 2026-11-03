#!/usr/bin/env python3
"""Replay only a disposable HOST cache image; never opens a tablet device."""
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
SOURCE=Path('/home/justin/xoom-p9-backup99/cache-p9.img')
EXPECTED='7053be21ae7e7c627aa829eafc97501cd5ceae2063f56177a4ce28488b3e4aef'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
if os.geteuid()!=0:raise SystemExit('Run with sudo to read the preserved root-only backup.')
if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size!=536870912 or digest(SOURCE)!=EXPECTED:
 raise SystemExit('Original backup identity mismatch; stopped.')
out=Path(tempfile.mkdtemp(prefix='xoom-p9-journal99-',dir='/home/justin'))
os.chmod(out,0o700);copy=out/'cache-working.img'
print('RESULT DIRECTORY:',out,flush=True)
shutil.copyfile(SOURCE,copy);os.chmod(copy,0o600)
with copy.open('rb') as f:os.fsync(f.fileno())
if digest(copy)!=EXPECTED:raise SystemExit('Copy mismatch; stopped.')
def run(name,args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'LC_ALL':'C'})
 (out/(name+'.log')).write_bytes(p.stdout)
 (out/(name+'.json')).write_text(json.dumps({'argv':args,'returncode':p.returncode},indent=2)+'\n')
 print(p.stdout.decode(errors='replace'),flush=True);print(name,'exit status:',p.returncode,flush=True)
 return p.returncode
replay=run('journal-replay',['e2fsck','-y','-E','journal_only,nodiscard',str(copy)])
if replay not in (0,1):raise SystemExit('Replay failed; stopped. Original/tablet unchanged.')
check=run('post-replay-fsck',['e2fsck','-f','-n','-E','no_optimize_extents',str(copy)])
run('post-replay-superblock',['dumpe2fs','-h',str(copy)])
result={'original_sha256':digest(SOURCE),'copy_sha256':digest(copy),'copy':str(copy),'fsck_exit':check,'tablet_accessed':False,'tablet_writes_authorized':False}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['original_sha256']==EXPECTED
print(json.dumps(result,indent=2));print('HOST COPY ONLY; review any remaining errors. Original backup unchanged.')
raise SystemExit(0 if check==0 else 2)
