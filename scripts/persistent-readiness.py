#!/usr/bin/env python3
"""Revalidate host evidence; never authorize, flash, mount RW or reboot."""
from pathlib import Path
import argparse,json,subprocess
from storage_host_evidence import validate_host_report,save_json
ROOT=Path(__file__).resolve().parents[1]
def readiness(host_report):
 result={key:False for key in ('DATA_FILESYSTEM_VERIFIED','DATA_BACKUP_VERIFIED',
  'DATA_WRITE_POLICY_VERIFIED','CACHE_FILESYSTEM_VERIFIED','CONTROLLED_WRITE_TEST_READY',
  'ANDROID_PERSISTENT_BOOT_READY')}
 result.update(writes_allowed=False,physical_write_executed=False,reasons=[])
 try:
  data=validate_host_report(host_report,require_healthy=False)
  result.update(DATA_FILESYSTEM_VERIFIED=data['filesystem_verified'],DATA_BACKUP_VERIFIED=True,data=data)
  result['reasons'].extend(data['filesystem_reasons'])
 except (OSError,ValueError,KeyError,TypeError) as e:result['reasons'].append('host_evidence: '+str(e))
 policy=subprocess.run(['python3',str(ROOT/'tests/test-storage-policy96.py')],capture_output=True,text=True)
 result['DATA_WRITE_POLICY_VERIFIED']=policy.returncode==0
 if policy.returncode:result['reasons'].append('compiled_policy_tests_failed')
 result['CONTROLLED_WRITE_TEST_READY']=all(result[k] for k in ('DATA_FILESYSTEM_VERIFIED','DATA_BACKUP_VERIFIED','DATA_WRITE_POLICY_VERIFIED'))
 # No source-mounted cache evidence or two-boot persistence evidence exists.
 # Android is a separate later gate, never inferred from a build or one file.
 result['reasons'].append('cache_unverified_use_tmpfs; controlled_two_boot_test_and_android_compatibility_pending')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host-inspection',type=Path,required=True)
 p.add_argument('--inspection',type=Path,help='original Android StageA report retained as additional evidence only')
 p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():p.error('refusing overwrite')
 result=readiness(a.host_inspection)
 if a.inspection:result['original_stage_a']=str(a.inspection.resolve())
 save_json(a.output,result);print(json.dumps(result,indent=2))
 raise SystemExit(0 if result['CONTROLLED_WRITE_TEST_READY'] else 2)
