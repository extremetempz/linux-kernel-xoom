#!/usr/bin/env python3
"""Send the fixed PSTORE request and save the bounded pstore/console output."""
from pathlib import Path
import argparse, array, base64, binascii, datetime, fcntl, getpass, hashlib, json, os, re, secrets, select, termios, time, tty
from diagnostic_protocol import handshake, write_request, ProtocolError
from pstore_protocol import extract_pstore_frame

ROOT = Path(__file__).resolve().parents[1]
P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--output-dir', type=Path, required=True)
P.add_argument('--port', type=Path)
P.add_argument('--timeout', type=int, default=90)
A = P.parse_args()
if not 5 <= A.timeout <= 300:
    P.error('timeout must be 5..300 seconds')
OUT = A.output_dir.resolve()
if not OUT.is_relative_to((ROOT/'artifacts').resolve()) or OUT.exists():
    P.error('Use a new private output directory under artifacts/')
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
if A.port:
    if A.port not in ports:
        P.error('Selected port is not the expected Xoom diagnostic ACM gadget')
    PORT = A.port
else:
    if len(ports) != 1:
        P.error('Require exactly one connected Xoom diagnostic ACM gadget')
    PORT = ports[0]
try:
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
except PermissionError:
    raise SystemExit(f'Host serial access needed. Run: sudo setfacl -m u:{getpass.getuser()}:rw {PORT}')
nonce = secrets.token_hex(16)
status = {'state':'started','nonce':nonce,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'request':'PSTORE','arbitrary_shell_commands':False}
try:
    OUT.mkdir(parents=True, exist_ok=False)
    tty.setraw(fd, termios.TCSANOW)
    attrs = termios.tcgetattr(fd)
    attrs[2] |= termios.CLOCAL | termios.CREAD
    attrs[4] = attrs[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    fcntl.ioctl(fd, termios.TIOCMBIS, array.array('i', [termios.TIOCM_DTR | termios.TIOCM_RTS]))
    wire = (OUT/'wire-private.bin').open('xb')
    handshake(fd, nonce, record=wire.write)
    print('Diagnostic reporter ready; sending fixed PSTORE snapshot.', flush=True)
    write_request(fd, 'PSTORE', nonce)
    buf = bytearray(); deadline = time.monotonic() + A.timeout; payload = None
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], 0.5)[0]:
            continue
        chunk = os.read(fd, 65536)
        if not chunk:
            raise ProtocolError('Serial device disconnected')
        wire.write(chunk); buf.extend(chunk)
        payload = extract_pstore_frame(buf, nonce)
        if payload is not None:
            break
    wire.close()
    if payload is None:
        raise TimeoutError('Timed out waiting for PSTORE result')
    if not payload.startswith(b'XOOM_PSTORE_REPORT_V1\n') or not payload.endswith(b'XOOM_PSTORE_REPORT_END\n'):
        raise ProtocolError('PSTORE payload markers missing')
    (OUT/'pstore-report.txt').write_bytes(payload)
    status.update(state='verified', bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    text = payload.decode('ascii','replace')
    for line in text.splitlines():
        if line.startswith(('PSTORE_', 'RAMOOPS_', 'CURRENT_BOOT_ID', 'XOOM_PSTORE_BOOT')):
            print(line, flush=True)
finally:
    try: (OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    except OSError: pass
    os.close(fd)
