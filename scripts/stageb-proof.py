#!/usr/bin/env python3
"""Validate two Stage B hardware reports; emit a sanitized build gate."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--first',type=Path,required=True);p.add_argument('--second',type=Path,required=True)
p.add_argument('--backup-sha256',required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.output.exists():p.error('use a new output file')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def one(path,marker):
 text=path.read_text(errors='replace')
 def val(pat):
  m=re.findall(pat,text,re.M);return m[-1] if m else None
 result={'report':str(path),'report_sha256':sha(path),'marker':marker}
 result['boot_id']=val(r'^BOOT_ID ([0-9a-f-]{36})$')
 result['uuid']=val(r'^DATA_FILESYSTEM_UUID ([0-9a-f]{32})$')
 result['write_rc']=val(r'^XOOM_STORAGE_WRITE_TEST_RC (\d+)$')
 result['unmount_rc']=val(r'^XOOM_STORAGE_WRITE_TEST_UNMOUNT_RC (\d+)$')
 result['p10_ro']=val(r'^XOOM_ANDROID44_BLOCK_RO mmcblk0p10 (\d)$')
 result['p9_ro']=val(r'^XOOM_ANDROID44_BLOCK_RO mmcblk0p9 (\d)$')
 result['marker_present']=marker in text
 if not result['boot_id'] or not result['uuid']:raise SystemExit('missing boot/uuid in '+str(path))
 if not result['marker_present'] or result['write_rc']!='0' or result['unmount_rc']!='0':
  raise SystemExit('Stage B report did not complete cleanly: '+str(path))
 if result['p10_ro']!='0' or result['p9_ro']!='1':
  raise SystemExit('Stage B policy mismatch: '+str(path))
 return result
first=one(a.first,'TEST_WRITE_OK_REBOOT_REQUIRED')
second=one(a.second,'TEST_FILE_PERSISTED_VERIFIED')
if first['boot_id']==second['boot_id']:raise SystemExit('Stage B boot IDs are identical')
if first['uuid']!=second['uuid']:raise SystemExit('Stage B filesystem UUID changed')
proof={'schema':'xoom-stageb-proof-v1','first':first,'second':second,
 'source_backup_sha256':a.backup_sha256,'stageb_two_boot_passed':True}
a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
