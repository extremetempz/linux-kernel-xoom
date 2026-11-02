#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
block='''XOOM_STORAGE_INSPECT_BEGIN
PART_START p9 2215936
PART_SIZE p9 1048576
PART_START p10 3264512
PART_SIZE p10 59247616
EXT4_MAGIC data 53ef
ANDROID_CRYPTO_FOOTER data absent
E2FSCK_N_RC data 0
RO_MOUNT_OK data
EXT4_MAGIC cache 53ef
ANDROID_CRYPTO_FOOTER cache absent
E2FSCK_N_RC cache 0
RO_MOUNT_OK cache
DATA_MOUNT_AFTER_INSPECTION
CACHE_MOUNT_AFTER_INSPECTION
XOOM_STORAGE_INSPECT_END
'''
with tempfile.TemporaryDirectory() as td:
 t=Path(td); (t/'report').write_text(block)
 subprocess.run([str(ROOT/'scripts/parse-storage-inspection.py'),'--report',str(t/'report'),'--output',str(t/'i.json')],check=True)
 i=json.loads((t/'i.json').read_text()); assert i['inspection_passed'] and i['verdict']=='healthy_unencrypted'
 # backup size/hash gate; sparse-size file is enough for this host-only test
 with (t/'backup').open('wb') as f: f.truncate(59247616*512)
 h=__import__('hashlib').sha256()
 with (t/'backup').open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''): h.update(c)
 r=subprocess.run([str(ROOT/'scripts/persistent-readiness.py'),'--inspection',str(t/'i.json'),'--backup',str(t/'backup'),'--backup-sha256',h.hexdigest(),'--output',str(t/'r.json')],check=True)
 assert json.loads((t/'r.json').read_text())['writes_allowed']
 # encrypted/missing fsck blocks
 bad=block.replace('ANDROID_CRYPTO_FOOTER data absent','ANDROID_CRYPTO_FOOTER data present_or_candidate')
 (t/'bad').write_text(bad)
 p=subprocess.run([str(ROOT/'scripts/parse-storage-inspection.py'),'--report',str(t/'bad'),'--output',str(t/'b.json')])
 assert p.returncode==2 and not json.loads((t/'b.json').read_text())['inspection_passed']
print('PASS Stage-A parser and backup/write readiness gate; no device I/O')
