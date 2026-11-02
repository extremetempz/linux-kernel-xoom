#!/usr/bin/env python3
"""Offline gates only: no ADB, block devices or image writes."""
from pathlib import Path
import copy
import runpy

module=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/recovery-storage-preflight.py'))
validate=module['validate']
def fixture():
    result={key:{'returncode':0,'stdout':value} for key,value in {
        'device':'wingray','bootmode':'recovery','identity':'uid=0(root) gid=0(root)',
        'disk_size':'62521344','disk_ro':'0','p10_ro':'0','p10_dev':'179:10',
        'mountinfo':'20 1 0:5 / / rw - rootfs rootfs rw',
        'swaps':'Filename\tType\tSize\tUsed\tPriority','p10_holders':'',
        'userdata_alias':'/dev/block/mmcblk0p10',
    }.items()}
    for n,(start,size) in module['GEOMETRY'].items():
        result[f'p{n}_start']={'returncode':0,'stdout':str(start)}
        result[f'p{n}_size']={'returncode':0,'stdout':str(size)}
    return result
good=fixture()
assert validate(good)['live_metadata_preflight_passed']
assert validate(good)['physical_writes_authorized'] is False
assert validate(good)['repair_environment_approved'] is False
for key,value in [('device','p4wifi'),('bootmode','normal'),('p10_start','989184'),
                  ('p10_size','999'),('identity','uid=2000(shell)'),('disk_size','999'),
                  ('p10_dev','8:0'),('p10_holders','dm-0'),('p10_ro',''),
                  ('userdata_alias','/dev/block/mmcblk0p9')]:
    broken=copy.deepcopy(good);broken[key]['stdout']=value
    assert not validate(broken)['live_metadata_preflight_passed'],key
for mount in ('21 20 179:10 / /mnt/data rw - ext4 /dev/block/mmcblk0p10 rw',
              '21 20 253:0 / /elsewhere rw - ext4 /dev/block/dm-0 rw',
              '21 20 179:8 / /system ro - ext4 /dev/block/mmcblk0p8 ro'):
    broken=copy.deepcopy(good);broken['mountinfo']['stdout']+='\n'+mount
    assert not validate(broken)['live_metadata_preflight_passed']
for key in ('mountinfo','p10_size','device'):
    broken=copy.deepcopy(good);del broken[key]
    assert not validate(broken)['live_metadata_preflight_passed']
broken=copy.deepcopy(good);broken['swaps']['stdout']+='\n/dev/block/mmcblk0p10 partition 1 0 -1'
assert not validate(broken)['live_metadata_preflight_passed']
print('PASS: metadata gate, legacy/mismatched BigPart, mounts/aliases, swap, holders, missing evidence; write approval always false')
