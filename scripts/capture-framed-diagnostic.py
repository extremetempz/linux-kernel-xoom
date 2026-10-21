#!/usr/bin/env python3
"""Capture a fresh verified Xoom report; fixed PING/REPORT requests only."""
from pathlib import Path
import argparse
import array
import datetime
import fcntl
import getpass
import hashlib
import json
import os
import re
import secrets
import termios
import tty
from diagnostic_protocol import handshake, write_request, receive_report, expected_geometry, storage_result

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output-dir', type=Path, required=True, help='New private directory under artifacts/')
p.add_argument('--port', type=Path, help='Expected gadget ttyACM node; autodetected when omitted')
p.add_argument('--expected-geometry', type=Path, default=root/'artifacts/hardware-private/geometry.txt')
p.add_argument('--expected-disk-sectors', type=int)
p.add_argument('--report-timeout', type=int, default=45)
a = p.parse_args()
if not 25 <= a.report_timeout <= 60:
    p.error('report-timeout must be between 25 and 60 seconds')
out = a.output_dir.resolve()
if not out.is_relative_to((root/'artifacts').resolve()) or out.exists():
    p.error('Use a new private output directory under artifacts/')
expected = expected_geometry(a.expected_geometry)
ports = []
for entry in Path('/sys/class/tty').glob('ttyACM*'):
    if not re.fullmatch(r'ttyACM[0-9]+', entry.name):
        continue
    current = (entry/'device').resolve()
    for usb in [current, *current.parents]:
        try:
            pair = ((usb/'idVendor').read_text().strip(), (usb/'idProduct').read_text().strip())
        except OSError:
            continue
        if pair == ('0525', 'a4a7'):
            ports.append(Path('/dev')/entry.name)
        break
if a.port:
    if a.port not in ports:
        p.error('Selected port is not the expected diagnostic USB ACM gadget')
    port = a.port
else:
    if len(ports) != 1:
        p.error('Require exactly one connected diagnostic USB ACM gadget')
    port = ports[0]
try:
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
except PermissionError:
    raise SystemExit(f'Host serial access needed. In your terminal run: sudo setfacl -m u:{getpass.getuser()}:rw {port}')
nonce = secrets.token_hex(16)
status = {'state': 'started', 'nonce': nonce,
          'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'requests': ['PING', 'REPORT'], 'arbitrary_shell_commands': False}
try:
    out.mkdir(parents=True, exist_ok=False)
    tty.setraw(fd, termios.TCSANOW)
    attrs = termios.tcgetattr(fd)
    attrs[2] |= termios.CLOCAL | termios.CREAD
    attrs[4] = attrs[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    fcntl.ioctl(fd, termios.TIOCMBIS, array.array('i', [termios.TIOCM_DTR | termios.TIOCM_RTS]))
    with (out/'wire-private.bin').open('xb') as wire:
        handshake(fd, nonce, record=wire.write)
        print('Verified diagnostic reporter is ready; requesting a fresh read-only report.', flush=True)
        write_request(fd, 'REPORT', nonce)
        payload = receive_report(fd, nonce, timeout=a.report_timeout, record=wire.write)
    (out/'report-private.txt').write_bytes(payload)
    geometry = storage_result(payload, expected, a.expected_disk_sectors)
    (out/'storage-result-private.json').write_text(json.dumps(geometry, indent=2)+'\n')
    status.update(state='verified', bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(), storage_state=geometry['state'])
    print('Report integrity verified. Storage result: '+geometry['state'], flush=True)
except Exception as exc:
    status.update(state='failed', error=f'{type(exc).__name__}: {exc}')
    raise
finally:
    if out.exists():
        (out/'capture-status.json').write_text(json.dumps(status, indent=2)+'\n')
    os.close(fd)
