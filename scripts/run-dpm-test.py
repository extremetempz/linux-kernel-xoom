#!/usr/bin/env python3
"""Run one full-tree devices-only DPM cycle; no platform or CPU sleep."""
from pathlib import Path
import argparse, array, base64, binascii, datetime, fcntl, getpass, hashlib, json, os, re, secrets, select, termios, time, tty
from diagnostic_protocol import handshake, write_request, ProtocolError

ROOT = Path(__file__).resolve().parents[1]
P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--output-dir', type=Path, required=True)
P.add_argument('--port', type=Path)
P.add_argument('--timeout', type=int, default=30)
A = P.parse_args()
if not 5 <= A.timeout <= 60:
    P.error('timeout must be 5..60 seconds')
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
          'request':'DPMTEST','arbitrary_shell_commands':False}
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
    print('Diagnostic reporter ready; requesting one devices-only DPM test.', flush=True)
    write_request(fd, status['request'], nonce)
    token = nonce.encode()
    header = re.compile(rb'(?:^|\n)XOOM_DPMTEST_V1 ' + token + rb' ([0-9]{1,6}) ([0-9a-f]{64})\r?\n')
    end = re.compile(rb'(?:^|\n)XOOM_DPMTEST_END_V1 ' + token + rb'\r?\n')
    err = re.compile(rb'(?:^|\n)XOOM_ERROR_V2 ' + token + rb' ([A-Z_]+)\r?\n')
    buf = bytearray(); deadline = time.monotonic() + A.timeout; payload = None
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], 0.5)[0]:
            continue
        chunk = os.read(fd, 65536)
        if not chunk:
            raise ProtocolError('Serial device disconnected')
        wire.write(chunk); buf.extend(chunk)
        if len(buf) > 600000:
            raise ProtocolError('DPMTEST response too large')
        match = err.search(buf)
        if match:
            raise ProtocolError('Device DPMTEST error: ' + match[1].decode())
        h = header.search(buf)
        if not h:
            continue
        size = int(h[1])
        if not 0 < size <= 65536:
            raise ProtocolError('Invalid DPMTEST size')
        e = end.search(buf, h.end())
        if not e:
            continue
        try:
            payload = base64.b64decode(b''.join(buf[h.end():e.start()].split()), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProtocolError('Invalid DPMTEST base64') from exc
        if len(payload) != size or hashlib.sha256(payload).hexdigest().encode() != h[2]:
            raise ProtocolError('DPMTEST size/hash mismatch')
        break
    wire.close()
    if payload is None:
        raise TimeoutError('Timed out waiting for DPMTEST result')
    if not payload.startswith(b'XOOM_DPM_TEST_V1\n') or not payload.endswith(b'XOOM_DPM_TEST_END\n'):
        raise ProtocolError('DPMTEST payload markers missing')
    (OUT/'dpm-test.txt').write_bytes(payload)
    status.update(state='verified', bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    lines=payload.splitlines()
    status['dpm_test_completed'] = all(x in lines for x in
        (b'DPMTEST_WRITE_RC 0',b'DPMTEST_COUNTER_ADVANCED_1',b'DPMTEST_PROCESS_RC 0'))
    status['whole_tree_device_suspend_tested'] = status['dpm_test_completed']
    status['cpu_sleep_tested'] = False
    text = payload.decode('ascii','replace')
    for line in text.splitlines():
        if line.startswith('DPMTEST_'):
            print(line, flush=True)
    if not status['dpm_test_completed']:
        raise SystemExit('DPM test failed; preserve the report and do not retry automatically')
finally:
    try: (OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    except OSError: pass
    os.close(fd)
