#!/usr/bin/env python3
"""Run actual bootstrap identity check on a read-only regular-file fixture."""
from pathlib import Path
import struct,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];s=(ROOT/'diagnostic/android44-gpu-bootstrap.sh').read_text()
a=s.index('verify_persistent_data() {');b=s.index('\n}\n',a)+3
with tempfile.TemporaryDirectory() as t:
 p=Path(t);dev=p/'device';approval=p/'approved';data=bytearray(2048)
 data[1128:1144]=b'X'*16;data[1116:1128]=bytes.fromhex('3c000000420200007b000000');data[1082:1084]=b'\1\0'
 dev.write_bytes(data);approval.write_text((b'X'*16).hex()+'\n'+data[1116:1128].hex()+'\n'+'a'*64+'\n')
 code=s[a:b].replace('/bin/busybox','/usr/bin/busybox').replace('/dev/mmcblk0p10',str(dev)).replace('/bin/storage-data-approved',str(approval))+'\nverify_persistent_data\n'
 def run():return subprocess.run(['/usr/bin/busybox','sh','-c',code],capture_output=True).returncode
 assert run()==0
 for offset in (1128,1116,1082,1428):
  original=dev.read_bytes();bad=bytearray(original);bad[offset]^=1;dev.write_bytes(bad)
  assert run()!=0;dev.write_bytes(original)
 approval.unlink();assert run()!=0
assert 'XOOM_STORAGE_WRITE_TEST_UNMOUNT_RC' in s
print('PASS actual RO bootstrap identity/features/clean-state/error-count binding; no real device')
