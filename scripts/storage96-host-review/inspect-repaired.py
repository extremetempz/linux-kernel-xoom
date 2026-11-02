#!/usr/bin/env python3
"""Read-only host-image metadata inspection; no mount, loop device or tablet access."""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import stat
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

helpers = runpy.run_path(str(Path(__file__).with_name('check-copy.py')))
digest, run, save = (helpers[n] for n in ('digest', 'run', 'save'))
IMAGE = Path('/home/justin/xoom-p10-preen96-2y07el_a/userdata-repair-experiment.img')
ORIGINAL = helpers['SOURCE']
SIZE = helpers['EXPECTED_BYTES']
PATHS = ('/', '/app', '/app-private', '/data', '/user', '/user/0', '/media', '/media/0',
         '/misc', '/misc/wifi', '/misc/wifi/sockets', '/misc/dhcp', '/misc/bluedroid',
         '/misc/bluetooth', '/system', '/system/users', '/system/users/0',
         '/dalvik-cache', '/local', '/local/tmp', '/local/xoom-storage-test', '/lost+found',
         '/system/packages.xml', '/system/packages.list', '/system/users/0/settings_secure.xml',
         '/misc/wifi/wpa_supplicant.conf')

def debug(query, limit=8*1024*1024):
    # This fixed command is deliberately never passed debugfs -w.
    result = subprocess.run(['debugfs', '-R', query, str(IMAGE)],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode or len(result.stdout) > limit:
        raise RuntimeError('Read-only debugfs failed or output exceeded review limit')
    return result.stdout.decode('utf-8', errors='replace'), result.stderr.decode('utf-8', errors='replace')

def metadata(path):
    text, error = debug('stat ' + path)
    if 'File not found' in error:
        return {'path': path, 'exists': False}
    match = re.search(r'Inode:\s*(\d+)\s+Type:\s*(.*?)\s+Mode:\s*([0-7]+)', text)
    owner = re.search(r'User:\s*(\d+)\s+Group:\s*(\d+).*?Size:\s*(\d+)', text)
    if not match or not owner:
        raise RuntimeError('Cannot interpret metadata for fixed path ' + path)
    label, label_error = debug('ea_get ' + path + ' security.selinux')
    result = {'path': path, 'exists': True, 'inode': int(match[1]), 'type': match[2],
              'mode': match[3], 'uid': int(owner[1]), 'gid': int(owner[2]), 'size': int(owner[3]),
              'selinux_label': label.strip().strip('\x00') or None,
              'selinux_label_present': bool(label.strip().strip('\x00'))}
    # Retain read-only error text only; no file contents are requested by stat/ea_get.
    if label_error.strip() != 'debugfs 1.47.0 (5-Feb-2023)':
        result['label_query_diagnostic'] = label_error.strip()
    return result

def read_regular(meta, maximum):
    if not meta.get('exists') or meta.get('type') != 'regular' or meta['size'] > maximum:
        return None
    content, errors = debug('cat ' + meta['path'], maximum)
    # Do not save/print this content or subprocess errors: it may contain credentials.
    if len(content.encode('utf-8')) > maximum or 'File not found' in errors:
        raise RuntimeError('Could not safely read fixed regular metadata file')
    return content

def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo; any password belongs only in the terminal')
    for path in (IMAGE, ORIGINAL):
        if path.is_symlink() or path.parent.is_symlink():
            raise RuntimeError('Symlink image path refused')
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != SIZE or info.st_nlink != 1:
            raise RuntimeError('Unexpected image type, size or hardlink count')
    out = Path(tempfile.mkdtemp(prefix='xoom-p10-layout96-', dir='/home/justin'))
    print('RESULT DIRECTORY: ' + str(out), flush=True)
    try:
        print('Verifying preserved original backup and hashing repaired copy...', flush=True)
        original_hash = digest(ORIGINAL)
        if original_hash != helpers['EXPECTED_SHA256']:
            raise RuntimeError('Original backup hash mismatch; stop for review')
        image_hash = digest(IMAGE)
        rc = run(out, 'repaired-fsck-readonly', ['e2fsck', '-f', '-n', '-E', 'no_optimize_extents', str(IMAGE)])
        sb_rc = run(out, 'repaired-superblock', ['dumpe2fs', '-h', str(IMAGE)])
        with IMAGE.open('rb') as f:
            f.seek(1024)
            sb = f.read(1024)
        complete = all('Pass ' + str(n) + ':' in (out / 'repaired-fsck-readonly.log').read_text(errors='replace') for n in range(1, 6))
        clean = (rc == 0 and sb_rc == 0 and complete and struct.unpack_from('<H', sb, 56)[0] == 0xef53
                 and struct.unpack_from('<H', sb, 58)[0] == 1
                 and not struct.unpack_from('<I', sb, 96)[0] & 4
                 and struct.unpack_from('<I', sb, 404)[0] == 0)
        if not clean:
            raise RuntimeError('Repaired image no longer passes non-modifying filesystem checks')
        print('Inspecting fixed Android metadata paths; credential contents suppressed...', flush=True)
        metas = {path: metadata(path) for path in PATHS}
        save(out / 'android-path-metadata.json', metas)
        listings = {}
        for path in ('/', '/app', '/data', '/user', '/media', '/misc', '/misc/wifi', '/system', '/lost+found'):
            if metas[path].get('type') == 'directory':
                text, error = debug('ls -p ' + path)
                listings[path] = {'listing': text, 'diagnostic': error}
        save(out / 'private-directory-metadata.json', listings)
        wifi_text = read_regular(metas['/misc/wifi/wpa_supplicant.conf'], 1024*1024)
        wifi = {'config_exists': metas['/misc/wifi/wpa_supplicant.conf']['exists'],
                'config_regular_and_readable': wifi_text is not None,
                'credential_or_ssid_values_recorded': False}
        if wifi_text is not None:
            wifi.update({'network_blocks': len(re.findall(r'^\s*network\s*=\s*\{', wifi_text, re.M)),
                         'ssid_fields': len(re.findall(r'^\s*ssid\s*=', wifi_text, re.M)),
                         'key_fields': len(re.findall(r'^\s*(?:psk|password|wep_key[0-3])\s*=', wifi_text, re.M)),
                         'uses_expected_socket_dir': bool(re.search(r'^\s*ctrl_interface\s*=.*?/data/misc/wifi/sockets(?:\s|$)', wifi_text, re.M))})
        wifi_text = None
        save(out / 'wifi-redacted-summary.json', wifi)
        packages = {'packages_xml_exists': metas['/system/packages.xml']['exists'], 'parsed': False}
        xml_text = read_regular(metas['/system/packages.xml'], 4*1024*1024)
        if xml_text is not None:
            try:
                root = ET.fromstring(xml_text)
                entries = root.findall('package')
                packages.update({'parsed': True, 'root_tag': root.tag, 'package_count': len(entries),
                    'last_platform_versions': [dict(n.attrib) for n in root.findall('last-platform-version')],
                    'version_records': [dict(n.attrib) for n in root.findall('version')]})
                samples = []
                for item in entries:
                    name = item.get('name', '')
                    uid = item.get('userId') or item.get('sharedUserId')
                    if not re.fullmatch(r'[A-Za-z0-9_.]+', name) or not uid or not uid.isdigit():
                        continue
                    data_path = '/system' if name == 'android' and item.get('codePath') == '/system/framework/framework-res.apk' and uid == '1000' else '/data/' + name
                    meta = metadata(data_path)
                    samples.append({'package': name, 'recorded_uid': int(uid), 'data_metadata': meta,
                                    'uid_matches': meta.get('uid') == int(uid) if meta.get('exists') else None})
                    if len(samples) == 32:
                        break
                save(out / 'private-package-uid-sample.json', samples)
                packages.update({'uid_samples': len(samples),
                    'existing_sample_dirs': sum(s['data_metadata']['exists'] for s in samples),
                    'uid_mismatches': sum(s['uid_matches'] is False for s in samples)})
            except ET.ParseError:
                packages['parse_error'] = 'XML parse failed; contents not recorded'
        save(out / 'package-metadata-summary.json', packages)
        print('Confirming read-only inspection left repaired image unchanged...', flush=True)
        if digest(IMAGE) != image_hash:
            raise RuntimeError('Repaired image changed during inspection; stop')
        save(out / 'repair-evidence.json', {
            'manual_repair_source': 'operator-provided terminal transcript in this chat; not automatically captured',
            'operator_reported_repairs': ['orphan inode list', 'free block count', 'free inode count', 'inode bitmap padding'],
            'original_previously_verified_sha256': original_hash,
            'original_preserved': True, 'journal_and_preen_logs_preserved_in_prior_directories': True,
            'fresh_readonly_check_exit': rc, 'file_content_integrity_proven': False})
        summary = {'repaired_image_path': str(IMAGE), 'bytes': SIZE, 'sha256': image_hash,
            'original_backup_sha256': original_hash, 'filesystem_check_passed': clean,
            'read_only_inspection_unchanged': True, 'uuid': sb[104:120].hex(),
            'existing_metadata_paths': sum(m['exists'] for m in metas.values()),
            'paths_with_selinux_labels': sum(m.get('selinux_label_present', False) for m in metas.values()),
            'wifi': wifi, 'packages': packages, 'tablet_accessed': False,
            'android_compatibility_verified': False, 'tablet_write_authorized': False,
            'remaining_review': ['compare labels/UIDs/layout with exact ROM init and file_contexts',
                                 'review repaired orphan consequences and existing app data',
                                 'review Wi-Fi socket compatibility without replacing credentials']}
        save(out / 'inspection-summary.json', summary)
        save(out / 'evidence-sha256.json', {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()})
        print(json.dumps(summary, indent=2), flush=True)
        print('INSPECTION COMPLETE; no tablet writes or mounts. RESULT DIRECTORY: ' + str(out), flush=True)
        return 0
    except Exception as e:
        # Do not put arbitrary parser/tool exceptions into public output: files can contain secrets.
        save(out / 'failure.json', {'exception_type': type(e).__name__, 'inspection_complete': False})
        print('INSPECTION BLOCKED (' + type(e).__name__ + '); preserve result directory for review.', flush=True)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
