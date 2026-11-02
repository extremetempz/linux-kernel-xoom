#!/usr/bin/env python3
"""Execute fixed StageB shell on private fixtures; no mounts or block devices."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];BB='/usr/bin/busybox'
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'data/local').mkdir(parents=True);(p/'run').mkdir();(p/'approved').touch()
 (p/'boot').write_text('11111111-1111-1111-1111-111111111111\n');(p/'ro').write_text('0\n')
 (p/'block').write_bytes(b'\0'*1128+b'1'*16)
 (p/'mounts').write_text(f'{p}/block {p}/data ext4 rw 0 0\n')
 wrapper=p/'bb';wrapper.write_text('''#!/bin/sh
if [ "$1" = id ]; then echo 0; exit 0; fi
if [ "$1" = stat ]; then
 v=$('''+BB+''' "$@") || exit 1
 echo "$v" | sed 's/^[0-9]*:[0-9]*:/0:0:/'
 exit 0
fi
exec '''+BB+''' "$@"
''');wrapper.chmod(0o755)
 s=(ROOT/'diagnostic/android44-storage-write-test.sh').read_text()
 for before,after in [('/proc/sys/kernel/random/boot_id',str(p/'boot')),('/sys/block/mmcblk0/mmcblk0p10/ro',str(p/'ro')),
  ('/dev/mmcblk0p10',str(p/'block')),('/proc/mounts',str(p/'mounts')),('/bin/storage-data-approved',str(p/'approved')),
  ('/data',str(p/'data')),('/run',str(p/'run')),('BB=/bin/busybox','BB='+str(wrapper))]:s=s.replace(before,after)
 script=p/'test';script.write_text(s)
 def run():return subprocess.run([BB,'sh',str(script)],capture_output=True)
 r=run();assert r.returncode==0,(r.stdout,r.stderr)
 assert b'TEST_WRITE_OK_REBOOT_REQUIRED' in r.stdout
 target=p/'data/local/xoom-storage-test/persistent-v1.bin';before=target.stat().st_mtime_ns
 assert len(target.read_bytes())==4120
 assert hashlib.sha256(target.read_bytes()).hexdigest()=='4f5a76d96d52a7902acb25f86971d101fc9fae1d7d97039fb6f0fbbb0a7e13ee'
 r=run();assert r.returncode and b'TEST_FILE_PRESENT_SAME_BOOT' in r.stdout
 assert target.stat().st_mtime_ns==before
 (p/'boot').write_text('22222222-2222-2222-2222-222222222222\n')
 r=run();assert r.returncode==0 and b'TEST_FILE_PERSISTED_VERIFIED' in r.stdout
 assert target.stat().st_mtime_ns==before
 os.link(target,p/'another-link');r=run();assert r.returncode and b'TEST_EXISTING_STATE_UNSAFE' in r.stdout
 (p/'another-link').unlink();target.unlink();target.symlink_to(p/'do-not-create')
 r=run();assert r.returncode and not (p/'do-not-create').exists()
print('PASS StageB create, same-boot refusal, second-boot verify-only and hardlink/symlink refusal; fixtures only')
