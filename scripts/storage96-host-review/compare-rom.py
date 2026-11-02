#!/usr/bin/env python3
"""Read-only comparison with pinned ROM references; never grants write readiness."""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from android44_image import original_entries, BOOT_SHA256, sections

inspect = runpy.run_path(str(HERE / 'inspect-repaired.py'))
digest, save = inspect['digest'], inspect['save']
IMAGE, ORIGINAL = inspect['IMAGE'], inspect['ORIGINAL']
REPORT = Path('/home/justin/xoom-p10-layout96-v1gdhvrd')
REPAIRED_SHA = '9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f'
IDS = {'root': 0, 'system': 1000, 'bluetooth': 1002, 'wifi': 1010,
       'media': 1013, 'dhcp': 1014, 'keystore': 1017, 'media_rw': 1023,
       'net_bt_stack': 3008, 'shell': 2000, 'cache': 2001, 'misc': 9998}
ORPHANS = [1273278,1273279,1273285,1273292,1273302,1273311,1273312,1273321,
           1273331,1273343,1273350,1273387,1273389,1273444,1273449,1273542,
           1273563,1273570,1273571,1273572]

def inode_query(image, query):
    result = subprocess.run(['debugfs', '-R', query, str(image)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise RuntimeError('Read-only inode query failed')
    return {'output': result.stdout.decode(errors='replace'),
            'diagnostic': result.stderr.decode(errors='replace')}

def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo')
    for p in (REPORT, IMAGE.parent, ORIGINAL.parent):
        if p.is_symlink():
            raise RuntimeError('Symlink path refused')
    if IMAGE.is_symlink() or ORIGINAL.is_symlink() or IMAGE.stat().st_size != inspect['SIZE']:
        raise RuntimeError('Unexpected image identity')
    receipt = json.loads((REPORT / 'inspection-summary.json').read_text())
    if receipt['sha256'] != REPAIRED_SHA or not receipt['filesystem_check_passed']:
        raise RuntimeError('Not the recorded passing repaired-image report')
    print('Checking repaired image hash before metadata comparison...', flush=True)
    if digest(IMAGE) != REPAIRED_SHA:
        raise RuntimeError('Repaired image changed since inspection')
    prior_hashes = json.loads((REPORT / 'evidence-sha256.json').read_text())
    for name in ('android-path-metadata.json', 'inspection-summary.json', 'wifi-redacted-summary.json'):
        if digest(REPORT / name) != prior_hashes[name]:
            raise RuntimeError('Inspection metadata changed')
    boot = (ROOT / 'artifacts/hardware-private/backup-boot.img').read_bytes()
    entries = original_entries(boot)  # Includes the pinned original boot hash check.
    expected = {}
    for name in ('init.rc', 'init.stingray.rc'):
        for header, commands in sections(entries[name].data.decode()):
            if not header.startswith('on '):
                continue
            for command in commands:
                parts = shlex.split(command)
                if parts[0] == 'mkdir' and len(parts) == 5 and (parts[1] == '/data' or parts[1].startswith('/data/')):
                    if parts[3] in IDS and parts[4] in IDS:
                        expected[parts[1]] = {'mode': int(parts[2],8), 'uid': IDS[parts[3]], 'gid': IDS[parts[4]], 'source': name}
                elif parts[0] == 'chmod' and len(parts) == 3 and parts[2].startswith('/data/'):
                    expected.setdefault(parts[2], {})['mode'] = int(parts[1],8)
    rules = []
    for line in entries['file_contexts'].data.decode().splitlines():
        parts = line.split()
        if parts and parts[0].startswith('/data') and len(parts) >= 2:
            rules.append((parts[0], parts[-1]))
    metas = json.loads((REPORT / 'android-path-metadata.json').read_text())
    comparison = []
    for path, meta in metas.items():
        rom_path = '/data' + (path if path != '/' else '')
        exp = expected.get(rom_path, {})
        mismatches = []
        if meta.get('exists'):
            for key in ('uid','gid','mode'):
                actual = int(meta['mode'],8) if key == 'mode' else meta[key]
                if key in exp and actual != exp[key]:
                    mismatches.append(key)
        matches = [label for regex,label in rules if re.fullmatch(regex, rom_path)]
        comparison.append({'image_path': path, 'rom_path': rom_path, 'exists': meta['exists'],
            'expected_init_metadata': exp, 'observed': meta,
            'metadata_mismatches': mismatches, 'matching_rom_context_rules': matches,
            'label_absent': meta.get('exists') and not meta.get('selinux_label_present', False),
            'label_rule_resolution': 'candidate rules only; not a replacement for libselinux file/type matching'})
    out = Path(tempfile.mkdtemp(prefix='xoom-p10-rom-compare96-', dir='/home/justin'))
    print('RESULT DIRECTORY: ' + str(out), flush=True)
    save(out / 'private-path-comparison.json', comparison)
    meta = inspect['metadata']('/system/packages.xml')
    text = inspect['read_regular'](meta, 4*1024*1024)
    if text is None:
        raise RuntimeError('Package metadata unavailable')
    package_root = ET.fromstring(text)
    checks = []
    for item in package_root.findall('package'):
        name = item.get('name','')
        uid = item.get('userId') or item.get('sharedUserId')
        if not re.fullmatch(r'[A-Za-z0-9_.]+', name) or not uid or not uid.isdigit():
            continue
        data_path = '/system' if name == 'android' and item.get('codePath') == '/system/framework/framework-res.apk' and uid == '1000' else '/data/' + name
        data = inspect['metadata'](data_path)
        checks.append({'package': name, 'expected_uid': int(uid), 'observed': data,
                       'uid_match': data.get('uid') == int(uid) if data['exists'] else None})
    save(out / 'private-all-package-uids.json', checks)
    print('Reading reported orphan inode metadata from preserved images; no file contents...', flush=True)
    evidence = []
    for ino in ORPHANS:
        row = {'inode': ino}
        for key,image in (('original',ORIGINAL),('repaired',IMAGE)):
            row[key] = {kind: inode_query(image, kind + ' <' + str(ino) + '>') for kind in ('testi','stat')}
        evidence.append(row)
    save(out / 'private-orphan-inode-comparison.json', evidence)
    versions = [dict(n.attrib) for n in package_root.findall('last-platform-version')]
    summary = {'original_boot_sha256': BOOT_SHA256, 'repaired_image_sha256': REPAIRED_SHA,
        'data_version_records': versions, 'checked_package_uid_records': len(checks),
        'existing_package_dirs': sum(c['observed']['exists'] for c in checks),
        'package_uid_mismatches': sum(c['uid_match'] is False for c in checks),
        'init_metadata_mismatches': [{'path': c['rom_path'], 'fields': c['metadata_mismatches'],
            'expected': c['expected_init_metadata'],
            'actual': {k:c['observed'].get(k) for k in ('mode','uid','gid')}} for c in comparison if c['metadata_mismatches']],
        'label_absent_paths': [c['rom_path'] for c in comparison if c['label_absent']],
        'linux44_selinux': 'disabled in tested kernel config; security LSM and ext4 security support not compiled',
        'original_kernel_selinux': 'compiled; runtime enforcing/permissive mode not established from saved evidence',
        'wifi': json.loads((REPORT / 'wifi-redacted-summary.json').read_text()),
        'orphan_inodes_compared': len(evidence),
        'orphan_content_preservation_proven': False,
        'no_copy_or_tablet_writes': True, 'android_persistent_boot_approved': False,
        'limitations': ['directory ownership is not app database/content integrity',
            'superblock free-count correction alone does not prove 88 allocations were removed; complete content integrity remains unproven',
            'missing labels require separate review before returning to SELinux-enabled original ROM',
            'no repair or restore of tablet has occurred']}
    save(out / 'comparison-summary.json', summary)
    save(out / 'evidence-sha256.json', {p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps(summary,indent=2), flush=True)
    print('COMPARISON COMPLETE; RESULT DIRECTORY: ' + str(out), flush=True)

if __name__ == '__main__':
    main()
