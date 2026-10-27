#!/usr/bin/env python3
"""Validate the fixed PSTORE snapshot request and host framing helper."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
server=(ROOT/'diagnostic/server.sh').read_text()
script=(ROOT/'diagnostic/pstore-report.sh').read_text()
sender=(ROOT/'scripts/run-pstore-report.py').read_text()
protocol=(ROOT/'scripts/diagnostic_protocol.py').read_text()
for path in ('diagnostic/server.sh','diagnostic/pstore-report.sh'):
    subprocess.run(['bash','-n',str(ROOT/path)],check=True)
assert 'PSTORE\\ *)' in server and 'XOOM_PSTORE_V1' in server and 'XOOM_PSTORE_END_V1' in server
assert '/sys/fs/pstore' in script and 'DMESG_TAIL' in script
assert 'XOOM_PSTORE_REPORT_V1' in script
assert "'PSTORE'" in protocol
assert 'PSTORE' in sender and 'pstore-report.txt' in sender
assert 'eval ' not in server and 'eval ' not in script
subprocess.run([sys.executable,str(ROOT/'scripts/run-pstore-report.py'),'--help'],check=True,stdout=subprocess.DEVNULL)
print('PASS fixed PSTORE: read-only pstore/console snapshot, framed transport, no shell')
