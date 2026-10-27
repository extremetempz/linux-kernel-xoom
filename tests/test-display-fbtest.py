#!/usr/bin/env python3
"""Validate the fixed FBTEST request, bounded fb write/restore, and host sender."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
server=(ROOT/'diagnostic/server.sh').read_text()
test=(ROOT/'diagnostic/fb-blank-test.sh').read_text()
sender=(ROOT/'scripts/run-fb-blank-test.py').read_text()
protocol=(ROOT/'scripts/diagnostic_protocol.py').read_text()
for path in ('diagnostic/server.sh','diagnostic/fb-blank-test.sh'):
 subprocess.run(['bash','-n',str(ROOT/path)],check=True)
assert 'FBTEST\\ *)' in server
assert 'XOOM_FBTEST_V1' in server and 'XOOM_FBTEST_END_V1' in server
assert 'fb-blank-test' in server
assert 'echo 4 > $FB' in test and 'echo 0 > $FB' in test
assert 'trap restore EXIT' in test and 'Wingray (display|backlight|DC test|native mode)' in test
assert 'eval ' not in server and 'eval ' not in test
assert "('PING', 'REPORT', 'FBTEST')" in protocol
assert 'FBTEST' in sender and 'fb-blank-test.txt' in sender
assert 'arbitrary_shell_commands' in sender and "'FBTEST'" in sender
subprocess.run([sys.executable,str(ROOT/'scripts/run-fb-blank-test.py'),'--help'],check=True,stdout=subprocess.DEVNULL)
print('PASS fixed FBTEST: bounded fb0 write/restore, framed result transport, no arbitrary shell')
