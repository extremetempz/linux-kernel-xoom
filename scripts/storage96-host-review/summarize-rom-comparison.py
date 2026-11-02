#!/usr/bin/env python3
"""Correct a report-only ID mapping and summarize existing private evidence."""
import json
import os
from pathlib import Path
import re
import runpy
import struct
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
tools = runpy.run_path(str(HERE / 'compare-rom.py'))
old = Path('/home/justin/xoom-p10-rom-compare96-11pwz237')
if os.geteuid() != 0:
    raise SystemExit('Run with sudo')
if old.is_symlink():
    raise SystemExit('Symlink report directory refused')
hashes = json.loads((old / 'evidence-sha256.json').read_text())
for name in ('comparison-summary.json','private-path-comparison.json','private-all-package-uids.json','private-orphan-inode-comparison.json'):
    if tools['digest'](old / name) != hashes[name]:
        raise SystemExit('Recorded evidence changed; stop for review')
boot = (tools['ROOT'] / 'artifacts/hardware-private/backup-boot.img').read_bytes()
init = tools['original_entries'](boot)['init'].data
# Derive the ID from the exact pinned ARM ELF init, not another Android release.
phoff = struct.unpack_from('<I',init,28)[0]
phsize,phnum = struct.unpack_from('<HH',init,42)
segments = [struct.unpack_from('<8I',init,phoff+i*phsize) for i in range(phnum)]
ids = set()
pos = 0
while True:
    pos = init.find(b'net_bt_stack\0',pos)
    if pos < 0:
        break
    for typ,off,va,pa,filesz,memsz,flags,align in segments:
        if typ != 1 or not off <= pos < off+filesz:
            continue
        ptr = struct.pack('<I',va+pos-off)
        at = 0
        while True:
            at = init.find(ptr,at)
            if at < 0:
                break
            if at % 4 == 0 and at+8 <= len(init):
                value = struct.unpack_from('<I',init,at+4)[0]
                if value < 100000:
                    ids.add(value)
            at += 1
    pos += 1
if ids != {3008}:
    raise SystemExit('Exact original init ID mapping ambiguous; stop')
rows = json.loads((old / 'private-path-comparison.json').read_text())
for row in rows:
    if row['rom_path'] == '/data/misc/bluedroid':
        row['expected_init_metadata']['gid'] = 3008
        observed = row['observed']
        expected = row['expected_init_metadata']
        row['metadata_mismatches'] = [key for key in ('mode','uid','gid') if key in expected and
            (int(observed[key],8) if key == 'mode' else observed[key]) != expected[key]]
checks = json.loads((old / 'private-all-package-uids.json').read_text())
missing = {row['package'] for row in checks if not row['observed']['exists']}
inspect = tools['inspect']
meta = inspect['metadata']('/system/packages.xml')
text = inspect['read_regular'](meta,4*1024*1024)
if text is None:
    raise SystemExit('Package metadata unreadable')
package_root = ET.fromstring(text)
missing_details = [{'package':item.get('name'), 'code_path':item.get('codePath'),
                    'recorded_uid':item.get('userId') or item.get('sharedUserId')}
                   for item in package_root.findall('package') if item.get('name') in missing]
orphans = json.loads((old / 'private-orphan-inode-comparison.json').read_text())
inode_summary = []
for row in orphans:
    result = {'inode':row['inode']}
    for side in ('original','repaired'):
        text = row[side]['stat']['output']
        links = re.search(r'Links:\s*(\d+)',text)
        owner = re.search(r'User:\s*(\d+)\s+Group:\s*(\d+).*?Size:\s*(\d+)',text)
        allocation = row[side]['testi']['output'].strip()
        result[side] = {'allocation':allocation, 'links':int(links[1]) if links else None,
            'uid':int(owner[1]) if owner else None, 'gid':int(owner[2]) if owner else None,
            'size':int(owner[3]) if owner else None}
    inode_summary.append(result)
summary = json.loads((old / 'comparison-summary.json').read_text())
summary['init_metadata_mismatches'] = [row for row in rows if row['metadata_mismatches']]
summary['bluetooth_gid_correction'] = {'old_checker_value':1028,'correct_value':3008,
    'verified_against':'numeric Android ID tables in pinned original ARM init binary',
    'userdata_gid_changed':False}
summary['missing_package_directories'] = missing_details
summary['orphan_inode_metadata'] = inode_summary
summary['no_tablet_or_image_writes'] = True
out = Path(tempfile.mkdtemp(prefix='xoom-p10-rom-corrected96-',dir='/home/justin'))
tools['save'](out / 'corrected-path-comparison.json',rows)
tools['save'](out / 'corrected-summary.json',summary)
tools['save'](out / 'source-report.json',{'path':str(old),'source_evidence_sha256':hashes})
tools['save'](out / 'evidence-sha256.json',{p.name:tools['digest'](p) for p in sorted(out.iterdir()) if p.is_file()})
print(json.dumps(summary,indent=2))
print('CORRECTED RESULT DIRECTORY: '+str(out))
