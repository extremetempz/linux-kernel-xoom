#!/usr/bin/env python3
"""Run the actual read-only report against fake full-sized pstore files."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / 'diagnostic/pstore-report.sh').read_text()
busybox = shutil.which('busybox')
assert busybox, 'Host busybox required'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    store = root / 'pstore'
    store.mkdir()
    names = ['dmesg-ramoops-0', 'dmesg-ramoops-1', 'dmesg-ramoops-2',
             'console-ramoops-0', 'pmsg-ramoops-0']
    for name in names:
        size = 0x80000 if name.startswith('console') else 0x20000
        (store / name).write_bytes(name.encode() + b'x'*(size-len(name)))
    before = {p.name: p.read_bytes() for p in store.iterdir()}
    mounts = root / 'mounts'
    mounts.write_text(f'pstore {store} pstore ro,nosuid,nodev,noexec 0 0\n')
    (root/'ecc-size').write_bytes(b'\0\0\0\x10')
    (root/'probe').write_text('fixture-current-probe\n')
    # Redirect only fixture paths and dmesg output. No mount, sysrq or live
    # device operations occur. The script itself retains read-only semantics.
    test = script.replace('/bin/busybox', busybox).replace('/sys/fs/pstore', str(store))
    test = test.replace('/proc/mounts', str(mounts)).replace('/proc/last_kmsg', str(root/'missing-kmsg'))
    test = test.replace('/sys/bus/platform/drivers/ramoops', str(root/'missing-driver'))
    test = test.replace('/sys/module/ramoops', str(root/'missing-module'))
    test = test.replace('/run/pstore-mount.txt', str(root/'missing-mount-log'))
    test = test.replace('/run/pstore-probe.txt', str(root/'probe'))
    test = test.replace('/proc/device-tree/ramoops@1ff00000/ecc-size', str(root/'ecc-size'))
    test = test.replace(f'{busybox} dmesg', f'{busybox} printf fixture-dmesg')
    result = subprocess.run(['/bin/sh', '-c', test], check=True, capture_output=True).stdout
    assert b'PSTORE_MOUNTED_yes' in result and b'RAMOOPS_BACKEND_UNBOUND' in result
    assert b'RAMOOPS_DT_ECC_HEX 00000010\n' in result
    assert b'PSTORE_CURRENT_PROBE_BEGIN\nfixture-current-probe\nPSTORE_CURRENT_PROBE_END' in result
    assert result.count(b'PSTORE_FILE_END') == 5
    assert len(result) > 1048576 and len(result) < 2097152
    assert b'PSTORE_TRUNCATED' not in result
    assert all(p.read_bytes() == before[p.name] for p in store.iterdir())
    # Above the cap, explicitly report truncation rather than silently lose
    # the transfer or allocate an unbounded host buffer.
    (store/'z-extra').write_bytes(b'y'*1048576)
    result = subprocess.run(['/bin/sh', '-c', test], check=True, capture_output=True).stdout
    assert b'PSTORE_TRUNCATED_TAIL' in result and len(result) < 2097152
print('PASS actual report preserves full configured console/records, explicit overflow truncation, no file writes/deletes')
