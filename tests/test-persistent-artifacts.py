#!/usr/bin/env python3
"""Offline verification of the three built persistent-storage artifacts."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
CASES=(('android44-persistent94-ready','wingray-android44-persistent.img','persistent'),
       ('android44-persistent94-inspect-ready','wingray-android44-persistent-inspect.img','inspect'),
       ('android44-persistent94-write-test-ready','wingray-android44-persistent-write-test.img','write'),
       ('android44-storage-backup94-ready','wingray-android44-storage-backup.img','backup'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for d,name,kind in CASES:
 p=ROOT/'artifacts'/d
 if not p.is_dir():
  print('SKIP missing artifact',d); continue
 m=json.loads((p/'manifest.json').read_text()); img=p/name
 assert sha(img)==m['sha256'] and img.stat().st_size==m['size'] and m['size']<8388608
 assert m['writes_authorized'] is False and m['userdata_backup_verified'] is False
 assert m['persistent_storage_profile'] is True
 assert (p/'SOURCE-COMMIT.txt').is_file() and (p/'boot-audit.json').is_file()
 audit=json.loads((p/'boot-audit.json').read_text())['diagnostic']; assert audit['sha256']==m['sha256']
 fstab=(p/'generated/fstab.stingray').read_text()
 assert ' /system ext4 ro,noload' in fstab and ' /data ext4 rw' in fstab and ' /cache ext4 rw' in fstab
 init=(p/'generated/init.rc').read_text(); assert 'mount_all' not in init
 if kind=='persistent': assert m['persistent_writes_enabled'] and not m['storage_inspection_only'] and not m['storage_write_test']
 if kind=='inspect': assert not m['persistent_writes_enabled'] and m['storage_inspection_only']
 if kind=='backup': assert m['storage_backup_profile'] and not m['persistent_writes_enabled']
 if kind=='write': assert m['persistent_writes_enabled'] and m['storage_write_test']
 dtb=(p/('tegra20-motorola-wingray-android44-'+('persistent-write-test' if kind=='write' else 'persistent-inspect' if kind=='inspect' else 'storage-backup' if kind=='backup' else 'persistent')+'.dtb')).read_bytes()
 assert b'motorola,xoom-firstboot-ro' not in dtb and b'motorola,xoom-persistent-storage' in dtb
 assert (b'motorola,wingray-storage-inspect' in dtb)==(kind=='inspect')
 assert (b'motorola,wingray-storage-write-test' in dtb)==(kind=='write')
 assert (b'motorola,wingray-storage-backup' in dtb)==(kind=='backup')
 print('PASS artifact',d,m['sha256'],m['size'])
print('PASS persistent artifact audit; no device operations')
