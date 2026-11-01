#!/usr/bin/env python3
"""Parse a read-only Wingray Stage-A report. Never contacts or writes a device."""
from pathlib import Path
import argparse, json, re

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists(): ap.error('refusing to overwrite output')
    text=a.report.read_text(errors='replace')
    begin=text.find('XOOM_STORAGE_INSPECT_BEGIN')
    end=text.find('XOOM_STORAGE_INSPECT_END',begin+1)
    result={'report':str(a.report),'complete':begin>=0 and end>begin,'filesystems':{},'writes_authorized':False}
    if not result['complete']:
        result['verdict']='incomplete'
        a.output.write_text(json.dumps(result,indent=2)+'\n'); print(result['verdict']); return 1
    block=text[begin:end+len('XOOM_STORAGE_INSPECT_END')]
    fields={}
    for line in block.splitlines():
        key,_,value=line.partition(' ')
        fields.setdefault(key,[]).append(value.strip())
    result['items']=fields
    for name in ('data','cache'):
        fs={'partition':name}
        magic=[l.split(' ',2)[2].strip() for l in block.splitlines() if l.startswith('EXT4_MAGIC '+name+' ')]
        fs['ext4_magic']=magic[-1] if magic else None
        footer=[l.split(' ',2)[2] for l in block.splitlines() if l.startswith('ANDROID_CRYPTO_FOOTER '+name+' ')]
        fs['crypto_footer']=footer[-1] if footer else None
        fsck=[l.rsplit(' ',1)[-1] for l in block.splitlines() if l.startswith('E2FSCK_N_RC '+name+' ')]
        fs['e2fsck_n_rc']=int(fsck[-1]) if fsck and fsck[-1].lstrip('-').isdigit() else None
        fs['ro_mount_ok']=any(l.startswith('RO_MOUNT_OK '+name) for l in block.splitlines())
        fs['mount_failed']=any(l.startswith('RO_MOUNT_FAILED '+name) for l in block.splitlines())
        result['filesystems'][name]=fs
    result['geometry_ok']=all(any(l==f'PART_START p{n} {start}' for l in block.splitlines()) and any(l==f'PART_SIZE p{n} {size}' for l in block.splitlines()) for n,start,size in ((9,2215936,1048576),(10,3264512,59247616)))
    result['data_unmounted_after']=not any(l.startswith('DATA_MOUNT_AFTER_INSPECTION ') and l.split(' ',1)[1].strip() for l in block.splitlines())
    result['cache_unmounted_after']=not any(l.startswith('CACHE_MOUNT_AFTER_INSPECTION ') and l.split(' ',1)[1].strip() for l in block.splitlines())
    reasons=[]
    if not result['geometry_ok']: reasons.append('geometry')
    for name,fs in result['filesystems'].items():
        if fs['ext4_magic']!='53ef': reasons.append(name+'_not_ext4')
        if fs['crypto_footer']!='absent': reasons.append(name+'_encrypted_or_unknown')
        if fs['e2fsck_n_rc']!=0: reasons.append(name+'_e2fsck_not_clean')
        if not fs['ro_mount_ok']: reasons.append(name+'_ro_mount_failed')
    if not result['data_unmounted_after'] or not result['cache_unmounted_after']: reasons.append('inspection_mount_left_active')
    result['reasons']=reasons
    result['verdict']='healthy_unencrypted' if not reasons else 'blocked'
    result['inspection_passed']=not reasons
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['verdict'])
    return 0 if not reasons else 2
if __name__=='__main__': raise SystemExit(main())
