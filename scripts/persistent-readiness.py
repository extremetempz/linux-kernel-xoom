#!/usr/bin/env python3
"""Gate Stage B/C on a clean Stage-A report plus a verified raw p10 backup."""
from pathlib import Path
import argparse, hashlib, json
P10_SECTORS=59247616
P10_BYTES=P10_SECTORS*512

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inspection',type=Path,required=True)
    ap.add_argument('--backup',type=Path,required=True)
    ap.add_argument('--backup-sha256',required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists(): ap.error('refusing to overwrite output')
    inspect=json.loads(a.inspection.read_text())
    reasons=[]
    if not inspect.get('inspection_passed'): reasons.append('inspection_not_passed')
    if inspect.get('verdict')!='healthy_unencrypted': reasons.append('not_healthy_unencrypted')
    if not a.backup.is_file(): reasons.append('backup_missing')
    else:
        if a.backup.stat().st_size!=P10_BYTES: reasons.append('backup_size_mismatch')
        h=hashlib.sha256()
        with a.backup.open('rb') as f:
            for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
        if h.hexdigest()!=a.backup_sha256.lower(): reasons.append('backup_sha256_mismatch')
    result={'inspection':str(a.inspection),'backup':str(a.backup),'expected_bytes':P10_BYTES,
            'backup_sha256':a.backup_sha256.lower(),'reasons':reasons,
            'writes_allowed':not reasons,'physical_write_executed':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2)); return 0 if not reasons else 2
if __name__=='__main__': raise SystemExit(main())
