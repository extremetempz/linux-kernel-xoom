#!/usr/bin/env python3
"""Bind p9 original/host-repair evidence. No tablet access or write authorization."""
import argparse,json,os,stat,subprocess
from pathlib import Path
from storage_host_evidence import validate_host_report,digest,superblock,save_json
SIZE=536870912
ORIGINAL='7053be21ae7e7c627aa829eafc97501cd5ceae2063f56177a4ce28488b3e4aef'
REPAIRED='8cf6c18b57eefbf19c31fd5ca81fe44ac016836af9fc97521f1dd80699e5527e'
def check_copy(path):
 path=Path(path)
 st=path.lstat()
 if not stat.S_ISREG(st.st_mode) or st.st_size!=SIZE:raise ValueError('require exact-size regular host copy, not symlink/device')
 if digest(path)!=REPAIRED:raise ValueError('repaired-copy hash mismatch')
 meta=superblock(path,SIZE)
 if meta['reasons']:raise ValueError('repaired filesystem metadata unhealthy: '+str(meta['reasons']))
 return meta

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--host-inspection',type=Path,required=True)
 p.add_argument('--repaired-copy',type=Path,required=True)
 p.add_argument('--output-dir',type=Path,required=True)
 a=p.parse_args()
 if a.output_dir.exists():p.error('use a new output directory; never overwrite evidence')
 if a.repaired_copy.is_symlink():p.error('no symlink copy')
 original=validate_host_report(a.host_inspection,partition='cache',require_healthy=False)
 if original['sha256']!=ORIGINAL:raise ValueError('unexpected original acquisition')
 meta=check_copy(a.repaired_copy)
 backup=a.host_inspection.resolve().parent/'cache-p9.img'
 if os.path.samefile(backup,a.repaired_copy):raise ValueError('copy must not alias original')
 a.output_dir.mkdir(mode=0o700)
 args=['e2fsck','-f','-n','-E','no_optimize_extents',str(a.repaired_copy.resolve())]
 result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'LC_ALL':'C'})
 (a.output_dir/'repaired-fsck-readonly.log').write_bytes(result.stdout)
 text=result.stdout.decode(errors='replace')
 from storage_host_evidence import fsck_output_has_errors
 passed=result.returncode==0 and all('Pass '+str(i)+':' in text for i in range(1,6)) and not fsck_output_has_errors(text)
 unchanged=digest(a.repaired_copy)==REPAIRED and digest(backup)==ORIGINAL
 receipt={'schema':'xoom-p9-offline-repair-preparation-v1','original':original,
 'repaired_copy':str(a.repaired_copy.resolve()),'repaired_sha256':REPAIRED,'repaired_metadata':meta,
 'fsck_argv':args,'fsck_exit':result.returncode,'fsck_log_sha256':digest(a.output_dir/'repaired-fsck-readonly.log'),
 'host_copy_check_passed':passed and unchanged,'preserved_hashes_unchanged':unchanged,
 'tablet_accessed':False,'physical_repair_authorized':False,'repair_image_ready':False,
 'remaining_gates':['p9-only kernel enforcement','pre-release mount/holder/swap exclusion',
 'same-image RAM checker validation','checked read-only rollback','explicit physical repair approval']}
 save_json(a.output_dir/'preparation.json',receipt)
 print(json.dumps(receipt,indent=2))
 raise SystemExit(0 if passed and unchanged else 2)
if __name__=='__main__':main()
