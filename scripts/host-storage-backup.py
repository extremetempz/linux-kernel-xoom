#!/usr/bin/env python3
"""Operator-invoked, read-only p10 USB inspection and two-pass backup; never flashes."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,mmap
from storage_host_evidence import *
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--device',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args();out=a.output_dir.resolve()
if os.geteuid()!=0:p.error('Run with sudo only after disabling desktop automount and identifying the LUN')
if out.exists():p.error('Use a new output directory on an independent host filesystem')
identity=source_identity(a.device)
# Refuse destination on source or any block device sharing that USB ancestor.
st=out.parent.stat();target=Path('/sys/dev/block')/f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}'
def backed_by_source(node,seen=None):
 seen=set() if seen is None else seen
 node=node.resolve()
 if node in seen:return False
 seen.add(node)
 if Path(identity['usb_sysfs']) in (node,*node.parents):return True
 if (node/'loop/backing_file').exists():
  backing=Path('/'+(node/'loop/backing_file').read_text().strip().lstrip('/'))
  bst=backing.stat();link=Path('/sys/dev/block')/f'{os.major(bst.st_dev)}:{os.minor(bst.st_dev)}'
  if not link.exists():raise ValueError('cannot establish loop backing filesystem')
  if backed_by_source(link,seen):return True
 return any(backed_by_source(n,seen) for n in (node/'slaves').glob('*'))
if not target.exists():p.error('destination filesystem backing is unknown; choose a local host block filesystem')
if backed_by_source(target):p.error('destination is on source USB device or a stacked alias')
if os.statvfs(out.parent).f_bavail*os.statvfs(out.parent).f_frsize<P10_BYTES+1024*1024*1024:p.error('require 32GB free host space')
out.mkdir(mode=0o700)
try:
 command(out,'kernel-before',['dmesg','--color=never'])
 if json.loads((out/'kernel-before.json').read_text())['returncode']!=0:raise ValueError('kernel log unavailable')
 save_json(out/'filesystem.json',superblock(a.device,P10_BYTES))
 command(out,'source-superblock',['dumpe2fs','-h',str(a.device.resolve())])
 command(out,'source-fsck',['e2fsck','-f','-n',str(a.device.resolve())])
 # Even dirty/encrypted media may be backed up read-only; readiness stays blocked.
 h=hashlib.sha256();total=0
 with a.device.open('rb',buffering=0) as src,(out/'userdata-p10.img').open('xb') as dst:
  os.chmod(out/'userdata-p10.img',0o600)
  while total<P10_BYTES:
   b=src.read(min(8*1024*1024,P10_BYTES-total))
   if not b:raise ValueError('short source read')
   if dst.write(b)!=len(b):raise ValueError('short backup write')
   total+=len(b);h.update(b)
  dst.flush();os.fsync(dst.fileno())
 directory_fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory_fd)
 finally:os.close(directory_fd)
 save_json(out/'acquisition.json',{'bytes':total,'sha256':h.hexdigest(),'source':identity})
 # Independent second complete source pass, not another hash of the backup.
 h=hashlib.sha256();total=0
 if source_identity(a.device)!=identity:raise ValueError('source changed')
 fd=os.open(a.device,os.O_RDONLY|os.O_DIRECT)
 try:
  with mmap.mmap(-1,8*1024*1024) as aligned:
   while total<P10_BYTES:
    view=memoryview(aligned)[:min(len(aligned),P10_BYTES-total)]
    try:
     n=os.readv(fd,[view])
     if not n:raise ValueError('short direct source read')
     h.update(view[:n]);total+=n
    finally:view.release()
 finally:os.close(fd)
 save_json(out/'source-second-read.json',{'bytes':total,'sha256':h.hexdigest(),'source':source_identity(a.device),'direct_io':True})
 command(out,'backup-superblock',['dumpe2fs','-h',str(out/'userdata-p10.img')])
 command(out,'backup-fsck',['e2fsck','-f','-n',str(out/'userdata-p10.img')])
 command(out,'kernel-after',['dmesg','--color=never'])
 r={'schema':'xoom-p10-host-v1','source':identity,'backup_path':str(out/'userdata-p10.img'),'physical_write_executed':False,
    'evidence_sha256':{n:digest(out/n) for n in ('kernel-before.log','kernel-after.log')}}
 save_json(out/'host-inspection.json',r)
 result=validate_host_report(out/'host-inspection.json',require_healthy=False)
 save_json(out/'verified-summary.json',result)
 print('DATA_BACKUP_VERIFIED; '+('DATA_FILESYSTEM_VERIFIED' if result['filesystem_verified'] else 'DATA_FILESYSTEM_BLOCKED')+'. No tablet writes authorized.')
 if not result['filesystem_verified']:raise SystemExit(2)
except (Exception,KeyboardInterrupt) as e:
 save_json(out/'failure.json',{'error':str(e),'physical_write_executed':False})
 raise SystemExit(str(e)+'; evidence/partial backup preserved; no automatic retry or repair')
