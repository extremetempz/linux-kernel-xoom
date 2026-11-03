#!/usr/bin/env python3
"""Synthetic report checks; no block devices are accessed."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
f=runpy.run_path(str(ROOT/'tests/test-diagnostic-protocol.py'))
from diagnostic_protocol import storage_result,ProtocolError

def body(cache=False):
 extras=[('/dev/mmcblk0p10','/data','ext4','rw,nosuid,nodev','179:10','/','rw')]
 extras.append(('/dev/mmcblk0p9','/cache','ext4','rw,nosuid,nodev','179:9','/','rw') if cache else ('tmpfs','/cache','tmpfs','rw,nosuid,nodev','0:7','/','rw'))
 data=f['android_body'](data_cache=False,extras=extras).replace(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p10 1',b'XOOM_ANDROID44_BLOCK_RO mmcblk0p10 0')
 if cache:data=data.replace(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 1',b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 0')
 return data

def check(data,mode):return storage_result(data,f['GEOMETRY'],62521344,storage_mode=mode)
for cache,mode in ((False,'android44-persistent'),(True,'android44-persistent-cache')):
 data=body(cache)
 assert check(data,mode)['state']=='geometry_matches_reference'
 for bad in (data.replace(b'179:10',b'179:9'),data.replace(b'/data rw',b'/data ro'),data.replace(b'BLOCK_RO mmcblk0 1',b'BLOCK_RO mmcblk0 0')):
  try:check(bad,mode)
  except ProtocolError:pass
  else:raise AssertionError('unsafe report accepted')
try:check(body(True),'android44-persistent')
except ProtocolError:pass
else:raise AssertionError('p9 accepted without explicit cache mode')
print('PASS: Stage C and explicit cache report identities and write flags')
