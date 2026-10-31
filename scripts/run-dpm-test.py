#!/usr/bin/env python3
"""One devices-only DPM cycle with USB re-enumeration and saved-status recovery."""
from pathlib import Path
import argparse, array, base64, binascii, datetime, fcntl, getpass, hashlib, json, os, re, secrets, select, termios, time, tty
from diagnostic_protocol import handshake, write_request, ProtocolError

ROOT = Path(__file__).resolve().parents[1]
P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--output-dir', type=Path, required=True)
P.add_argument('--port', type=Path)
P.add_argument('--timeout', type=int, default=30, help='DPM window before treating USB as suspended')
P.add_argument('--reconnect-timeout', type=int, default=90)
A = P.parse_args()
if not 5 <= A.timeout <= 60 or not 10 <= A.reconnect_timeout <= 180:
    P.error('timeout 5..60; reconnect-timeout 10..180')
OUT = A.output_dir.resolve()
if not OUT.is_relative_to((ROOT/'artifacts').resolve()) or OUT.exists():
    P.error('Use a new private output directory under artifacts/')

def matching_ports():
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
    return ports

def choose_port(previous=None):
    ports = matching_ports()
    if A.port:
        if A.port not in ports:
            raise ProtocolError('Selected port is not the expected Xoom diagnostic ACM gadget')
        return A.port
    if len(ports) != 1:
        raise ProtocolError('Require exactly one Xoom diagnostic ACM gadget')
    return ports[0]

def open_port(port):
    try:
        fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except PermissionError:
        raise SystemExit(f'Host serial access needed. Run: sudo setfacl -m u:{getpass.getuser()}:rw {port}')
    tty.setraw(fd, termios.TCSANOW)
    attrs = termios.tcgetattr(fd)
    attrs[2] |= termios.CLOCAL | termios.CREAD
    attrs[4] = attrs[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    fcntl.ioctl(fd, termios.TIOCMBIS, array.array('i', [termios.TIOCM_DTR | termios.TIOCM_RTS]))
    return fd

def read_frame(fd, token, header_name, end_name, limit=600000):
    header = re.compile(rb'(?:^|\n)' + header_name + rb' ' + token + rb' ([0-9]{1,7}) ([0-9a-f]{64})\r?\n')
    end = re.compile(rb'(?:^|\n)' + end_name + rb' ' + token + rb'\r?\n')
    err = re.compile(rb'(?:^|\n)XOOM_ERROR_V2 ' + token + rb' ([A-Z_]+)\r?\n')
    buf = bytearray()
    while True:
        if not select.select([fd], [], [], 0.5)[0]:
            continue
        chunk = os.read(fd, 65536)
        if not chunk:
            raise ConnectionError('serial disconnected')
        buf.extend(chunk)
        if len(buf) > limit:
            raise ProtocolError('response too large')
        match = err.search(buf)
        if match:
            raise ProtocolError('device error: ' + match[1].decode())
        h = header.search(buf)
        if not h:
            continue
        size = int(h[1])
        e = end.search(buf, h.end())
        if not e:
            continue
        try:
            payload = base64.b64decode(b''.join(buf[h.end():e.start()].split()), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProtocolError('invalid base64 response') from exc
        if len(payload) != size or hashlib.sha256(payload).hexdigest().encode() != h[2]:
            raise ProtocolError('response size/hash mismatch')
        return payload

def boot_id(fd, nonce):
    write_request(fd, 'BOOTID', nonce)
    buf = bytearray()
    deadline = time.monotonic() + 10
    pattern = re.compile(rb'XOOM_BOOTID_V1 ' + nonce.encode() + rb' ([0-9a-f-]{36})\r?\n')
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], 0.5)[0]:
            continue
        chunk = os.read(fd, 4096)
        if not chunk:
            raise ConnectionError('serial disconnected')
        buf.extend(chunk)
        m = pattern.search(buf)
        if m:
            return m[1].decode()
    raise TimeoutError('timed out reading boot ID')

def dpm_status(fd, nonce):
    write_request(fd, 'DPMSTATUS', nonce)
    return read_frame(fd, nonce.encode(), b'XOOM_DPMSTATUS_V1', b'XOOM_DPMSTATUS_END_V1')

def dpm_payload(fd, nonce):
    write_request(fd, 'DPMTEST', nonce)
    return read_frame(fd, nonce.encode(), b'XOOM_DPMTEST_V1', b'XOOM_DPMTEST_END_V1')

def config(fd):
    return (termios.tcgetattr(fd)[4] == termios.B115200)

def parse_dpm(payload):
    lines = payload.splitlines()
    before = next((x for x in lines if x.startswith(b'DPMTEST_BEFORE ')), None)
    after = next((x for x in lines if x.startswith(b'DPMTEST_AFTER ')), None)
    bid = next((x for x in lines if x.startswith(b'DPMTEST_BOOT_ID ')), None)
    if not before or not after or not bid:
        raise ProtocolError('DPM status lacks boot ID or counter')
    bm = re.search(rb'completed=([0-9]+)', before)
    am = re.search(rb'completed=([0-9]+)', after)
    if not bm or not am or int(am[1]) != int(bm[1]) + 1:
        raise ProtocolError('DPM counter did not advance exactly once')
    if b'last_result=0' not in after:
        raise ProtocolError('DPM result was not zero')
    return {'counter_before': int(bm[1]), 'counter_after': int(am[1]),
            'boot_id': bid.split()[1].decode()}

port = choose_port()
fd = open_port(port)
nonce = secrets.token_hex(16)
status = {'state':'started','nonce':nonce,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'request':'DPMTEST','arbitrary_shell_commands':False,'port':str(port)}
try:
    OUT.mkdir(parents=True, exist_ok=False)
    wire = (OUT/'wire-private.bin').open('xb')
    handshake(fd, nonce, record=wire.write)
    initial_boot = boot_id(fd, nonce)
    status['initial_boot_id'] = initial_boot
    print('Diagnostic reporter ready; requesting one devices-only DPM test.', flush=True)
    payload = None
    disconnected = False
    try:
        payload = dpm_payload(fd, nonce)
    except (ConnectionError, OSError):
        disconnected = True
        status['usb_disconnected'] = True
        wire.write(b'\n[DPMTEST transport disconnected]\n')
    if payload is not None:
        (OUT/'dpm-test.txt').write_bytes(payload)
        info = parse_dpm(payload)
        status.update(state='verified', recovery='direct', bytes=len(payload),
                      sha256=hashlib.sha256(payload).hexdigest(), **info)
    else:
        try: os.close(fd)
        except OSError: pass
        deadline = time.monotonic() + A.reconnect_timeout
        new_fd = None
        while time.monotonic() < deadline:
            try:
                new_port = choose_port()
                new_fd = open_port(new_port)
                status['reconnected_port'] = str(new_port)
                break
            except (OSError, ProtocolError):
                time.sleep(1)
        if new_fd is None:
            status.update(state='unresolved', error='USB gadget did not re-enumerate')
            raise SystemExit('DPM result unresolved: USB gadget did not re-enumerate; do not retry')
        fd = new_fd
        status['usb_reconnected'] = True
        nonce2 = secrets.token_hex(16)
        handshake(fd, nonce2, record=wire.write)
        new_boot = boot_id(fd, nonce2)
        status['reconnect_boot_id'] = new_boot
        if new_boot != initial_boot:
            status.update(state='failed', error='boot ID changed across DPM test')
            raise SystemExit('DPM test crossed a reboot; result is not attributable')
        status_payload = dpm_status(fd, nonce2)
        (OUT/'dpm-status.txt').write_bytes(status_payload)
        info = parse_dpm(status_payload)
        if info['boot_id'] != initial_boot:
            status.update(state='failed', error='saved DPM result belongs to another boot')
            raise SystemExit('Saved DPM result belongs to another boot')
        status.update(state='verified', recovery='reconnect', bytes=len(status_payload),
                      sha256=hashlib.sha256(status_payload).hexdigest(), **info)
    print('DPM verified:', json.dumps({k:status[k] for k in ('boot_id','counter_before','counter_after','recovery')}), flush=True)
finally:
    try: (OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    except OSError: pass
    try: os.close(fd)
    except OSError: pass
