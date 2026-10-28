#!/usr/bin/env python3
"""Execute the actual opt-in boot-probe block against temporary files."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'diagnostic/android44-init.sh').read_text()
start = source.index(' if [ -e /proc/device-tree/motorola,wingray-pstore-ecc-test ]; then')
block = source[start:source.index('\n fi', start) + len('\n fi')]
busybox = shutil.which('busybox')
assert busybox
boot = '5a938e4d-83e4-4bdb-a8c5-1370ef46fa72'
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p/'boot_id').write_text(boot+'\n')
    test = block.replace('/bin/busybox', busybox)
    for path, target in (('/proc/device-tree/motorola,wingray-pstore-ecc-test','enabled'),
                         ('/proc/sys/kernel/random/boot_id','boot_id'),
                         ('/run/pstore-probe.txt','probe'), ('/dev/kmsg','kmsg')):
        test = test.replace(path, str(p/target))
    subprocess.run(['/bin/sh', '-c', test], check=True)
    assert not (p/'probe').exists() and not (p/'kmsg').exists()
    (p/'enabled').touch()
    subprocess.run(['/bin/sh', '-c', test], check=True)
    pattern = '0123456789abcdef'*16
    digest = hashlib.sha256((boot+' '+pattern).encode()).hexdigest()
    expected = f'XOOM_PSTORE_PROBE_V1 {boot} {pattern} {digest}\n'.encode()
    assert (p/'probe').read_bytes() == (p/'kmsg').read_bytes() == expected
    assert len(expected) > 2*128
print('PASS actual boot probe: opt-in only, exact boot/pattern/hash, spans multiple ECC blocks; no device writes')
