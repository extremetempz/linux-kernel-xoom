"""Read-only host evidence and readiness validation for the fixed BigPart p10."""
from pathlib import Path
import hashlib,json,os,re,stat,struct,subprocess,fcntl,array
P10_BYTES=30334779392
P9_BYTES=536870912
USB=('0525','a4a5')
def volume_spec(partition):
 if partition=='data':return P10_BYTES,'userdata-p10.img','xoom-p10-host-v1'
 if partition=='cache':return P9_BYTES,'cache-p9.img','xoom-p9-host-v1'
 raise ValueError('unknown partition purpose')
def fsck_output_has_errors(text):
 return bool(re.search(r'Free (?:blocks|inodes) count wrong|Padding at end of .*bitmap|corrupted orphan linked list|Filesystem still has errors|Fix\?\s*no',text,re.I))
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save_json(path,data):
 with Path(path).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def superblock(path,size):
 with Path(path).open('rb',buffering=0) as f:
  f.seek(1024);b=f.read(1024);f.seek(size-16384);tail=f.read(16384)
 if len(b)!=1024 or len(tail)!=16384:raise ValueError('short superblock/footer read')
 u16=lambda n:struct.unpack_from('<H',b,n)[0]
 u32=lambda n:struct.unpack_from('<I',b,n)[0]
 compat,inc,ro=u32(92),u32(96),u32(100)
 blocks=u32(4)+(u32(336)<<32 if inc&128 else 0)
 log=u32(24);blocksize=1024<<log if log<=6 else 0
 reasons=[]
 if u16(56)!=0xef53:reasons.append('not_ext4')
 if u16(58)!=1 or u16(60) not in (1,2,3):reasons.append('not_clean_or_bad_error_policy')
 if u32(404):reasons.append('recorded_filesystem_errors')
 # Initial conservative Linux4.4 feature subset. Unknown features block RW.
 if compat & ~(4|8|16|32):reasons.append('unreviewed_compat_features')
 if inc & ~(2|64|128|512):reasons.append('unsupported_or_recovery_incompat_features')
 if ro & ~(1|2|8|16|32|64):reasons.append('unreviewed_ro_compat_features')
 if not compat&4:reasons.append('journal_required')
 if not blocksize or not blocks or blocks*blocksize>size:reasons.append('filesystem_bounds')
 if b'\xc4\xb1\xb5\xd0' in tail or inc&0x10000:reasons.append('encryption_or_candidate')
 return {'uuid':b[104:120].hex(),'state':u16(58),'error_count':u32(404),
  'compat':compat,'incompat':inc,'ro_compat':ro,'blocks':blocks,'block_size':blocksize,
  'superblock_sha256':hashlib.sha256(b).hexdigest(),'footer_sha256':hashlib.sha256(tail).hexdigest(),
  'reasons':reasons}
def command(out,name,args):
 # Retain complete stdout+stderr, including nonzero fsck results; no shell.
 with (out/(name+'.log')).open('xb') as f:
  p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'LC_ALL':'C'})
 receipt={'argv':args,'returncode':p.returncode,'log':name+'.log','sha256':digest(out/(name+'.log'))}
 save_json(out/(name+'.json'),receipt);return receipt

def source_identity(path,partition='data'):
 path=Path(path).resolve(strict=True);st=path.stat()
 if not stat.S_ISBLK(st.st_mode):raise ValueError('source must be a block device')
 key=f'{os.major(st.st_rdev)}:{os.minor(st.st_rdev)}'
 sys=Path('/sys/dev/block')/key;real=sys.resolve(strict=True)
 if (real/'partition').exists():raise ValueError('require exported LUN disk, not a host partition')
 usb=None
 for parent in (real,*real.parents):
  if (parent/'idVendor').exists():usb=parent;break
 if usb is None or ((usb/'idVendor').read_text().strip(),(usb/'idProduct').read_text().strip())!=USB:
  raise ValueError('not expected Linux file-storage USB gadget 0525:a4a5')
 nodes={key}
 for n in real.glob('*/dev'):
  if (n.parent/'partition').exists():nodes.add(n.read_text().strip())
 for line in Path('/proc/self/mountinfo').read_text().splitlines():
  if line.split()[2] in nodes:raise ValueError('source or its child is mounted; stop desktop automount first')
 for line in Path('/proc/swaps').read_text().splitlines()[1:]:
  if Path(line.split()[0]).resolve()==path:raise ValueError('source used as swap')
 with path.open('rb',buffering=0) as f:
  ro=array.array('i',[0]);fcntl.ioctl(f,0x125e,ro,True)
  size=array.array('Q',[0]);fcntl.ioctl(f,0x80001272 | (struct.calcsize('P')<<16),size,True)
 if ro[0]!=1 or size[0]!=volume_spec(partition)[0]:raise ValueError('source not RO or selected volume capacity mismatch')
 return {'path':str(path),'major_minor':key,'sysfs':str(real),'usb_sysfs':str(usb),
         'serial':(usb/'serial').read_text().strip() if (usb/'serial').exists() else None,
         'bytes':size[0],'ro':ro[0]}

def validate_host_report(report,rehash=True,require_healthy=True,partition='data'):
 """Re-read raw evidence and image; booleans in JSON are not readiness proof."""
 report=Path(report).resolve();r=json.loads(report.read_text());out=report.parent
 size,filename,schema=volume_spec(partition)
 if r.get('schema')!=schema:raise ValueError('wrong partition evidence schema')
 if r.get('source',{}).get('bytes')!=size or r['source'].get('ro')!=1:raise ValueError('bad source size/RO')
 backup=(out/filename);st=backup.stat()
 if not stat.S_ISREG(st.st_mode) or backup.is_symlink() or st.st_size!=size:raise ValueError('backup size/type')
 recorded_backup=r.get('backup_path')
 if not isinstance(recorded_backup,str) or Path(recorded_backup).name!=filename:raise ValueError('recorded backup target missing')
 filesystem_reasons=[]
 for name in ('source-fsck','backup-fsck','source-superblock','backup-superblock'):
  rec=json.loads((out/(name+'.json')).read_text())
  if rec['log']!=name+'.log' or digest(out/rec['log'])!=rec['sha256']:raise ValueError('changed tool evidence')
  if rec['returncode']!=0:filesystem_reasons.append(name+' not clean; inspect complete output')
  expected=['e2fsck','-f','-n'] if name.endswith('fsck') else ['dumpe2fs','-h']
  expected_target=recorded_backup if name.startswith('backup-') else r['source']['path']
  if rec['argv']!=expected+[expected_target]:raise ValueError('inspection command/target mismatch')
  text=(out/rec['log']).read_text(errors='replace')
  if name.endswith('fsck') and fsck_output_has_errors(text):
   filesystem_reasons.append(name+' unresolved filesystem errors in output')
  # Exit0 without actual completed fsck phases/output must not establish health.
  if name.endswith('fsck') and not all(x in text for x in ('Pass 1:','Pass 2:','Pass 3:','Pass 4:','Pass 5:')):
   filesystem_reasons.append('incomplete '+name+' output')
  if name.endswith('superblock') and ('Filesystem state:' not in text or 'Filesystem features:' not in text):
   filesystem_reasons.append('incomplete '+name+' output')
 meta=superblock(backup,size)
 filesystem_reasons.extend(meta['reasons'])
 if meta!=json.loads((out/'filesystem.json').read_text()):raise ValueError('backup filesystem metadata changed')
 first=json.loads((out/'acquisition.json').read_text());second=json.loads((out/'source-second-read.json').read_text())
 if first.get('bytes')!=size or second.get('bytes')!=size:raise ValueError('incomplete read')
 if first.get('source')!=r['source'] or second.get('source')!=r['source']:raise ValueError('source identity changed')
 if second.get('direct_io') is not True:raise ValueError('independent direct source read missing')
 if first.get('sha256')!=second.get('sha256'):raise ValueError('independent source read mismatch')
 if rehash and digest(backup)!=first.get('sha256'):raise ValueError('backup hash mismatch')
 for name in ('kernel-before.log','kernel-after.log'):
  if digest(out/name)!=r['evidence_sha256'].get(name):raise ValueError('kernel evidence changed')
 before=(out/'kernel-before.log').read_text(errors='replace').splitlines()
 after=(out/'kernel-after.log').read_text(errors='replace').splitlines()
 # Require full original prefix so log rotation cannot hide transfer errors.
 if after[:len(before)]!=before:raise ValueError('kernel log rotated; cannot establish I/O evidence')
 if re.search(r'I/O error|Buffer I/O|blk_update_request|reset .*USB|USB disconnect|device descriptor read|mmc.*error',
              '\n'.join(after[len(before):]),re.I):raise ValueError('I/O/USB error observed; manual review required')
 if require_healthy and filesystem_reasons:raise ValueError(','.join(filesystem_reasons))
 return {'partition':partition,'filesystem_verified':not filesystem_reasons,'filesystem_reasons':filesystem_reasons,'backup_verified':True,
         'sha256':first['sha256'],'uuid':meta['uuid'],'source':r['source'],'report':str(report)}
