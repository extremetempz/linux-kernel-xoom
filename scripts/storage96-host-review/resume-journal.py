#!/usr/bin/env python3
"""Continue the one verified disposable copy after the terminal-mode refusal."""
import json
import os
from pathlib import Path
import runpy
import stat
import struct

helpers = runpy.run_path(str(Path(__file__).with_name('check-copy.py')))
digest, run, save = (helpers[n] for n in ('digest', 'run', 'save'))
expected = helpers['EXPECTED_SHA256']
out = Path('/home/justin/xoom-p10-journal-check96-bt5ecxev')
copy = out / 'userdata-working.img'
if os.geteuid() != 0:
    raise SystemExit('Run with sudo')
if out.is_symlink() or copy.is_symlink():
    raise SystemExit('Symlink refused')
st = copy.stat()
if not stat.S_ISREG(st.st_mode) or st.st_size != helpers['EXPECTED_BYTES'] or st.st_nlink != 1:
    raise SystemExit('Unexpected disposable copy identity/size')
if json.loads((out / 'journal-replay.json').read_text())['returncode'] != 8:
    raise SystemExit('Not the recorded terminal-mode refusal')
if (out / 'journal-replay-noninteractive.log').exists():
    raise SystemExit('This continuation was already attempted; preserve evidence and review')
print('Verifying existing disposable copy before any change...', flush=True)
if digest(copy) != expected:
    raise SystemExit('Copy changed; stop for review. No replay attempted.')
print('Hash matches the verified original; replaying only the host copy journal.', flush=True)
journal_rc = run(out, 'journal-replay-noninteractive', ['e2fsck', '-p', '-E', 'journal_only', str(copy)])
if journal_rc not in (0, 1):
    raise SystemExit('Replay stopped; preserve logs. No full repair or tablet access performed.')
rc = run(out, 'post-replay-fsck', ['e2fsck', '-f', '-n', '-E', 'no_optimize_extents', str(copy)])
sb_rc = run(out, 'post-replay-superblock', ['dumpe2fs', '-h', str(copy)])
with copy.open('rb') as f:
    f.seek(1024)
    sb = f.read(1024)
incompat = struct.unpack_from('<I', sb, 96)[0]
state = struct.unpack_from('<H', sb, 58)[0]
errors = struct.unpack_from('<I', sb, 404)[0]
text = (out / 'post-replay-fsck.log').read_text(errors='replace')
complete = all('Pass ' + str(n) + ':' in text for n in range(1, 6))
clean = rc == 0 and sb_rc == 0 and not incompat & 4 and state == 1 and errors == 0 and complete
save(out / 'result.json', {'host_copy_check_passed': clean, 'journal_exit': journal_rc,
    'post_replay_fsck_exit': rc, 'needs_recovery': bool(incompat & 4),
    'filesystem_state': state, 'error_count': errors, 'original_backup_sha256': expected,
    'tablet_accessed': False, 'tablet_write_authorized': False})
print('COPY CHECK ' + ('PASSED' if clean else 'BLOCKED') + '; original backup and tablet unchanged.', flush=True)
print('RESULT DIRECTORY: ' + str(out), flush=True)
raise SystemExit(0 if clean else 2)
