#!/usr/bin/env python3
"""Replay only a disposable host copy; never open a tablet device for writing."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile

SOURCE = Path('/home/justin/xoom-p10-backup96/userdata-p10.img')
EXPECTED_BYTES = 30334779392
EXPECTED_SHA256 = 'c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579'

def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def run(out, name, argv):
    with (out / (name + '.log')).open('xb') as log:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                env={**os.environ, 'LC_ALL': 'C'})
    save(out / (name + '.json'), {'argv': argv, 'returncode': result.returncode})
    print((out / (name + '.log')).read_text(errors='replace'), flush=True)
    print(name + ' exit status: ' + str(result.returncode), flush=True)
    return result.returncode

def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo; enter any password only in the terminal')
    if SOURCE.parent.is_symlink() or SOURCE.is_symlink():
        raise RuntimeError('Source symlink refused')
    fd = os.open(SOURCE, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as src:
        before = os.fstat(src.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != EXPECTED_BYTES:
            raise RuntimeError('Source must be the exact-size regular backup file')
        if shutil.disk_usage('/home/justin').free < EXPECTED_BYTES + 1024**3:
            raise RuntimeError('Insufficient host space')
        out = Path(tempfile.mkdtemp(prefix='xoom-p10-journal-check96-', dir='/home/justin'))
        print('RESULT DIRECTORY: ' + str(out), flush=True)
        copy = out / 'userdata-working.img'
        try:
            h = hashlib.sha256()
            print('Copying host backup; no tablet access...', flush=True)
            with copy.open('xb') as dst:
                os.chmod(copy, 0o600)
                total = 0
                for block in iter(lambda: src.read(8 * 1024 * 1024), b''):
                    if dst.write(block) != len(block):
                        raise RuntimeError('Short host write')
                    h.update(block)
                    total += len(block)
                dst.flush()
                os.fsync(dst.fileno())
            after = os.fstat(src.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise RuntimeError('Source changed during copy')
            print('Verifying disposable copy...', flush=True)
            if total != EXPECTED_BYTES or h.hexdigest() != EXPECTED_SHA256 or digest(copy) != EXPECTED_SHA256:
                raise RuntimeError('Copy/source does not match verified acquisition hash; no journal replay performed')
            save(out / 'copy-before-replay.json', {'bytes': total, 'sha256': EXPECTED_SHA256, 'source': str(SOURCE)})
            journal_rc = run(out, 'journal-replay', ['e2fsck', '-p', '-E', 'journal_only', str(copy)])
            if journal_rc not in (0, 1):
                raise RuntimeError('Journal replay failed; no further modification attempted')
            rc = run(out, 'post-replay-fsck', ['e2fsck', '-f', '-n', '-E', 'no_optimize_extents', str(copy)])
            sb_rc = run(out, 'post-replay-superblock', ['dumpe2fs', '-h', str(copy)])
            with copy.open('rb') as f:
                f.seek(1024)
                sb = f.read(1024)
            incompat = struct.unpack_from('<I', sb, 96)[0]
            state = struct.unpack_from('<H', sb, 58)[0]
            error_count = struct.unpack_from('<I', sb, 404)[0]
            complete = all('Pass ' + str(n) + ':' in (out / 'post-replay-fsck.log').read_text(errors='replace') for n in range(1, 6))
            clean = rc == 0 and sb_rc == 0 and not incompat & 4 and state == 1 and error_count == 0 and complete
            save(out / 'result.json', {'host_copy_check_passed': clean, 'journal_exit': journal_rc,
                'post_replay_fsck_exit': rc, 'needs_recovery': bool(incompat & 4),
                'filesystem_state': state, 'error_count': error_count, 'original_backup_sha256': EXPECTED_SHA256,
                'tablet_accessed': False, 'tablet_write_authorized': False})
            print('COPY CHECK ' + ('PASSED' if clean else 'BLOCKED') + '; original backup and tablet unchanged.', flush=True)
            print('RESULT DIRECTORY: ' + str(out), flush=True)
            return 0 if clean else 2
        except Exception as e:
            save(out / 'failure.json', {'error': str(e), 'tablet_accessed': False})
            print('STOPPED: ' + str(e) + '; all host evidence preserved at ' + str(out), flush=True)
            return 2

if __name__ == '__main__':
    raise SystemExit(main())
