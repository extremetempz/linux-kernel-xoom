#!/usr/bin/env python3
"""Read-only recovery metadata collection; never unmount, repair, reboot or flash."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

GEOMETRY = {
    1:(51200,6144), 2:(57344,4096), 3:(61440,4096), 4:(65536,8192),
    5:(73728,4096), 6:(77824,24576), 7:(102400,16384),
    8:(118784,2097152), 9:(2215936,1048576), 10:(3264512,59247616),
}

def validate(readings):
    reasons=[]
    def value(key):
        row=readings.get(key,{})
        if row.get('returncode') != 0:
            reasons.append('unavailable_'+key)
            return ''
        return row.get('stdout','').strip()
    if value('device') != 'wingray': reasons.append('not_wingray')
    if not re.search(r'\buid=0\b',value('identity')): reasons.append('not_root_recovery_shell')
    if value('bootmode') != 'recovery': reasons.append('recovery_bootmode_not_confirmed')
    if value('disk_size') != '62521344': reasons.append('disk_capacity_mismatch')
    for number,(start,size) in GEOMETRY.items():
        if value(f'p{number}_start') != str(start): reasons.append(f'p{number}_start_mismatch')
        if value(f'p{number}_size') != str(size): reasons.append(f'p{number}_size_mismatch')
    if value('p10_dev') != '179:10': reasons.append('p10_device_number_mismatch')
    if value('userdata_alias') != '/dev/block/mmcblk0p10': reasons.append('userdata_alias_mismatch')
    mounts=value('mountinfo')
    for line in mounts.splitlines():
        columns=line.split()
        if len(columns)<10 or '-' not in columns:
            reasons.append('unparsed_mountinfo');continue
        separator=columns.index('-')
        source=columns[separator+2] if len(columns)>separator+2 else ''
        # Refuse all eMMC mounts/aliases and any mapper, not just a /data mount.
        if columns[2].startswith(('179:','253:')) or columns[4] in ('/data','/cache','/system') or re.match(r'/dev/(?:block/)?dm-',source):
            reasons.append('emmc_or_android_filesystem_mounted')
    if not mounts: reasons.append('empty_mountinfo')
    swaps=value('swaps').splitlines()
    if len(swaps)!=1 or not swaps[0].startswith('Filename'):
        reasons.append('swap_active_or_unknown')
    holders=value('p10_holders')
    if holders: reasons.append('p10_has_block_holders')
    if value('disk_ro') not in ('0','1') or value('p10_ro') not in ('0','1'):
        reasons.append('unknown_readonly_policy')
    # This report is a necessary metadata check, never sufficient write approval.
    return {'live_metadata_preflight_passed':not reasons, 'blockers':sorted(set(reasons)),
            'expected_userdata_bytes':30334779392,
            'toolchain_verified':False, 'recovery_automount_behaviour_verified':False,
            'repair_environment_approved':False, 'physical_writes_authorized':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True,help='Explicit recovery ADB transport serial')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists():parser.error('Use a new private output directory')
    queries={
        'device':['getprop','ro.product.device'], 'bootmode':['getprop','ro.bootmode'],
        'identity':['id'], 'kernel':['uname','-r'],
        'disk_size':['cat','/sys/class/block/mmcblk0/size'],
        'disk_ro':['cat','/sys/class/block/mmcblk0/ro'],
        'p10_dev':['cat','/sys/class/block/mmcblk0p10/dev'],
        'p10_ro':['cat','/sys/class/block/mmcblk0p10/ro'],
        'p10_holders':['ls','/sys/class/block/mmcblk0p10/holders'],
        'mountinfo':['cat','/proc/self/mountinfo'], 'swaps':['cat','/proc/swaps'],
        'fstab':['cat','/etc/recovery.fstab'], 'twrp_fstab':['cat','/etc/twrp.fstab'],
        'userdata_alias':['readlink','-f','/dev/block/platform/sdhci-tegra.3/by-name/userdata'],
    }
    for number in GEOMETRY:
        for item in ('start','size'):
            queries[f'p{number}_{item}']=['cat',f'/sys/class/block/mmcblk0p{number}/{item}']
    args.output_dir.mkdir(mode=0o700,parents=False)
    readings={}
    for name,command in queries.items():
        # Commands are fixed metadata reads; no caller-supplied device commands.
        try:
            result=subprocess.run(['adb','-s',args.serial,'shell',*command],
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,timeout=15)
            readings[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        except subprocess.TimeoutExpired:
            readings[name]={'returncode':124,'stdout':'','stderr':'metadata query timed out'}
            break
    report=validate(readings)
    report['transport_serial_sha256']=hashlib.sha256(args.serial.encode()).hexdigest()
    report['queries_executed']=len(readings)
    (args.output_dir/'private-readings.json').write_text(json.dumps(readings,indent=2)+'\n')
    (args.output_dir/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['live_metadata_preflight_passed'] else 2

if __name__=='__main__':
    raise SystemExit(main())
