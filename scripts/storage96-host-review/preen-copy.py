#!/usr/bin/env python3
"""One conservative repair experiment on a new, private host image only."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import struct
import tempfile

helpers = runpy.run_path(str(Path(__file__).with_name('check-copy.py')))
digest, run, save = (helpers[n] for n in ('digest', 'run', 'save'))
source_dir = Path('/home/justin/xoom-p10-journal-check96-bt5ecxev')
source = source_dir / 'userdata-working.img'
size = helpers['EXPECTED_BYTES']

def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run with sudo; enter any password only in the terminal')
    if source_dir.is_symlink() or source.is_symlink():
        raise RuntimeError('Source symlink refused')
    prior = json.loads((source_dir / 'result.json').read_text())
    if prior['journal_exit'] != 0 or prior['post_replay_fsck_exit'] != 4 or prior['needs_recovery']:
        raise RuntimeError('Not the expected journal-replayed, blocked host copy')
    if shutil.disk_usage('/home/justin').free < size + 1024**3:
        raise RuntimeError('Insufficient host space for another copy')
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as src:
        before = os.fstat(src.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != size or before.st_nlink != 1:
            raise RuntimeError('Unexpected source file identity/size')
        src.seek(1024)
        original_sb = src.read(1024)
        src.seek(0)
        out = Path(tempfile.mkdtemp(prefix='xoom-p10-preen96-', dir='/home/justin'))
        image = out / 'userdata-repair-experiment.img'
        print('RESULT DIRECTORY: ' + str(out), flush=True)
        try:
            print('Copying journal-replayed host image; no tablet access...', flush=True)
            h = hashlib.sha256()
            total = 0
            with image.open('xb') as dst:
                os.chmod(image, 0o600)
                for block in iter(lambda: src.read(8 * 1024 * 1024), b''):
                    if dst.write(block) != len(block):
                        raise RuntimeError('Short host copy write')
                    h.update(block)
                    total += len(block)
                dst.flush()
                os.fsync(dst.fileno())
            after = os.fstat(src.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise RuntimeError('Source changed while copying')
            print('Verifying new disposable copy...', flush=True)
            if total != size or digest(image) != h.hexdigest():
                raise RuntimeError('Copy verification failed; no repair attempted')
            save(out / 'before-repair.json', {'source': str(source), 'bytes': total,
                'source_and_copy_sha256': h.hexdigest(), 'uuid': original_sb[104:120].hex()})
            rc = run(out, 'preen', ['e2fsck', '-f', '-p', '-E', 'fixes_only,nodiscard', str(image)])
            if rc not in (0, 1):
                save(out / 'result.json', {'host_copy_check_passed': False, 'preen_exit': rc,
                    'reason': 'preen stopped; review logs; no further repair attempted',
                    'tablet_accessed': False, 'original_backup_modified': False})
                print('COPY CHECK BLOCKED; preen requires review. No automatic retry.', flush=True)
                print('RESULT DIRECTORY: ' + str(out), flush=True)
                return 2
            check_rc = run(out, 'post-preen-fsck', ['e2fsck', '-f', '-n', '-E', 'no_optimize_extents', str(image)])
            sb_rc = run(out, 'post-preen-superblock', ['dumpe2fs', '-h', str(image)])
            with image.open('rb') as f:
                f.seek(1024)
                sb = f.read(1024)
            incompat = struct.unpack_from('<I', sb, 96)[0]
            state = struct.unpack_from('<H', sb, 58)[0]
            errors = struct.unpack_from('<I', sb, 404)[0]
            complete = all('Pass ' + str(n) + ':' in (out / 'post-preen-fsck.log').read_text(errors='replace') for n in range(1, 6))
            clean = (check_rc == 0 and sb_rc == 0 and complete and state == 1
                     and not incompat & 4 and errors == 0 and sb[104:120] == original_sb[104:120]
                     and image.stat().st_size == size)
            print('Hashing repaired experiment for its evidence record...', flush=True)
            save(out / 'result.json', {'host_copy_check_passed': clean, 'preen_exit': rc,
                'post_preen_fsck_exit': check_rc, 'needs_recovery': bool(incompat & 4),
                'filesystem_state': state, 'error_count': errors,
                'repaired_experiment_sha256': digest(image),
                'tablet_accessed': False, 'original_backup_modified': False,
                'journal_copy_modified': False, 'tablet_write_authorized': False})
            print('COPY CHECK ' + ('PASSED' if clean else 'BLOCKED') + '; review repair log before any next step.', flush=True)
            print('RESULT DIRECTORY: ' + str(out), flush=True)
            return 0 if clean else 2
        except Exception as e:
            save(out / 'failure.json', {'error': str(e), 'tablet_accessed': False})
            print('STOPPED: ' + str(e) + '; evidence preserved at ' + str(out), flush=True)
            return 2

if __name__ == '__main__':
    raise SystemExit(main())
