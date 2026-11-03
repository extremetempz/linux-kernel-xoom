#!/usr/bin/env python3
"""Host-only filesystem evidence checks on temporary regular files."""
from pathlib import Path
import importlib.util,json,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import storage_host_evidence as evidence
from storage_host_evidence import superblock,validate_host_report,source_identity,digest,save_json
spec=importlib.util.spec_from_file_location('ready',ROOT/'scripts/persistent-readiness.py');ready=importlib.util.module_from_spec(spec);spec.loader.exec_module(ready)
class Evidence(unittest.TestCase):
 def test_cache_purpose_and_fsck_output(self):
  self.assertEqual(evidence.volume_spec('cache'),(536870912,'cache-p9.img','xoom-p9-host-v1'))
  self.assertTrue(evidence.fsck_output_has_errors('Free blocks count wrong (1, counted=2).\nFix? no'))
  self.assertFalse(evidence.fsck_output_has_errors('Pass 5: Checking group summary information'))
  report=self.p.parent/'wrong-purpose.json'
  report.write_text(json.dumps({'schema':'xoom-p10-host-v1','source':{'bytes':536870912,'ro':1}}))
  with self.assertRaises(ValueError):validate_host_report(report,partition='cache')
  report.write_text(json.dumps({'schema':'xoom-p9-host-v1','source':{'bytes':30334779392,'ro':1}}))
  with self.assertRaises(ValueError):validate_host_report(report)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'fs.img';self.n=2*1024*1024
  b=bytearray(self.n);struct.pack_into('<I',b,1028,1024);struct.pack_into('<I',b,1048,0)
  struct.pack_into('<HHH',b,1080,0xef53,1,1);struct.pack_into('<III',b,1116,4|8|16|32,2|64|512,1|2|16|32|64)
  self.p.write_bytes(b)
 def tearDown(self):self.tmp.cleanup()
 def test_clean_features(self):self.assertEqual(superblock(self.p,self.n)['reasons'],[])
 def test_dirty_recovery_errors_unknown(self):
  for offset,value,fmt in [(1082,2,'H'),(1120,4|2|64,'I'),(1428,1,'I'),(1124,0x80000000,'I')]:
   old=self.p.read_bytes();b=bytearray(old);struct.pack_into('<'+fmt,b,offset,value);self.p.write_bytes(b)
   self.assertTrue(superblock(self.p,self.n)['reasons']);self.p.write_bytes(old)
 def test_encryption_tail(self):
  with self.p.open('r+b') as f:f.seek(self.n-16384);f.write(b'\xc4\xb1\xb5\xd0')
  self.assertIn('encryption_or_candidate',superblock(self.p,self.n)['reasons'])
 def test_short_and_block_identity(self):
  self.p.write_bytes(b'short')
  with self.assertRaises((ValueError,OSError)):superblock(self.p,self.n)
  with self.assertRaises(ValueError):source_identity(self.p)
 def test_boolean_not_evidence(self):
  p=self.p.parent/'fake.json';p.write_text(json.dumps({'inspection_passed':True,'backup_verified':True,'writes_allowed':True}))
  with self.assertRaises(ValueError):validate_host_report(p)
  result=ready.readiness(p)
  self.assertFalse(result['CONTROLLED_WRITE_TEST_READY']);self.assertFalse(result['ANDROID_PERSISTENT_BOOT_READY'])
  self.assertFalse(result['DATA_BACKUP_VERIFIED']);self.assertFalse(result['CACHE_FILESYSTEM_VERIFIED'])
 def test_bound_bundle_and_tampering(self):
  out=self.p.parent;backup=out/'userdata-p10.img';backup.write_bytes(self.p.read_bytes())
  source={'bytes':self.n,'ro':1,'path':'/dev/test-fixture'}
  save_json(out/'filesystem.json',superblock(backup,self.n))
  for name in ('source-fsck','backup-fsck','source-superblock','backup-superblock'):
   text='\n'.join('Pass '+str(i)+':' for i in range(1,6)) if name.endswith('fsck') else 'Filesystem state: clean\nFilesystem features: has_journal'
   (out/(name+'.log')).write_text(text)
   args=(['e2fsck','-f','-n'] if name.endswith('fsck') else ['dumpe2fs','-h'])+[str(backup) if name.startswith('backup-') else source['path']]
   save_json(out/(name+'.json'),{'argv':args,'returncode':0,'log':name+'.log','sha256':digest(out/(name+'.log'))})
  rec={'bytes':self.n,'sha256':digest(backup),'source':source}
  save_json(out/'acquisition.json',rec);save_json(out/'source-second-read.json',{**rec,'direct_io':True})
  for n in ('kernel-before.log','kernel-after.log'):(out/n).write_text('baseline\n')
  report=out/'host-inspection.json';save_json(report,{'schema':'xoom-p10-host-v1','source':source,'backup_path':str(backup),
   'evidence_sha256':{n:digest(out/n) for n in ('kernel-before.log','kernel-after.log')}})
  old=evidence.P10_BYTES;evidence.P10_BYTES=self.n
  try:
   self.assertTrue(validate_host_report(report)['backup_verified'])
   rec_path=out/'backup-fsck.json';rec=json.loads(rec_path.read_text());rec['returncode']=4;rec_path.write_text(json.dumps(rec))
   blocked=validate_host_report(report,require_healthy=False)
   self.assertTrue(blocked['backup_verified']);self.assertFalse(blocked['filesystem_verified'])
   with self.assertRaises(ValueError):validate_host_report(report)
   rec['returncode']=0;rec_path.write_text(json.dumps(rec))
   before=(out/'backup-fsck.log').read_bytes();(out/'backup-fsck.log').write_bytes(b'altered')
   with self.assertRaises(ValueError):validate_host_report(report)
   (out/'backup-fsck.log').write_bytes(before)
   second=json.loads((out/'source-second-read.json').read_text());second['sha256']='0'*64
   (out/'source-second-read.json').write_text(json.dumps(second))
   with self.assertRaises(ValueError):validate_host_report(report)
  finally:evidence.P10_BYTES=old
 def test_bare_host_schema_insufficient(self):
  p=self.p.parent/'fake.json';p.write_text(json.dumps({'schema':'xoom-p10-host-v1','source':{'bytes':30334779392,'ro':1}}))
  with self.assertRaises(OSError):validate_host_report(p)
if __name__=='__main__':unittest.main()
