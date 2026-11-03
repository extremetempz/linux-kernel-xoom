#!/usr/bin/env python3
"""Reject marker-only or contradictory offline cache reports."""
from pathlib import Path
import runpy,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
f=runpy.run_path(str(R/'tests/test-diagnostic-protocol.py'))
from diagnostic_protocol import storage_result,ProtocolError
ram='\n'.join(['CLEAN_CHECK_EXIT 0','COUNTER_BEFORE_EXIT 4','COUNTER_REPAIR_EXIT 1','COUNTER_AFTER_EXIT 0','JOURNAL_BEFORE_EXIT 4','JOURNAL_REPLAY_EXIT 0','PADDING_BEFORE_EXIT 4','PADDING_REPAIR_EXIT 1','PADDING_AFTER_EXIT 0','RAMTEST_EXIT 0','CACHE99_RAM_JOURNAL_PADDING_PASSED'])
s='XOOM_OFFLINE97_BEGIN\n'+ram+'\nXOOM_OFFLINE97_END\nXOOM_CACHE99_POLICY_BEGIN\nCACHE99_ATTEMPTED 0\nCACHE99_RAM_STATE passed\n'
s+=f['storage_body'](capacity=62521344).decode().replace('62521344 0','62521344 1')
s+=''.join(f'CACHE99_RO mmcblk0p{i} 1\n' for i in range(1,11))+'XOOM_CACHE99_POLICY_END\n'
def check(t):return storage_result(t.encode(),f['GEOMETRY'],62521344,storage_mode='offline-cache99')
assert check(s)['state']=='cache99_readonly_ramtest_passed'
for bad in (s.replace('PADDING_AFTER_EXIT 0',''),s.replace('ATTEMPTED 0','ATTEMPTED 1'),s.replace('mmcblk0p10 1','mmcblk0p10 0'),s.replace('62521344 1','62521344 0'),s.replace('rootfs / rootfs','/dev/mmcblk0p9 /cache ext4'),s.replace('RAMTEST_EXIT 0','RAMTEST_EXIT 4')):
 try:check(bad)
 except ProtocolError:pass
 else:raise AssertionError('unsafe/incomplete report accepted')
print('PASS cache99 actual RAM-phase outcomes and live geometry/RO/mount/attempt gates')
