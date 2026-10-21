"""Bounded, nonce-correlated diagnostic transport. No device writes beyond fixed requests."""
import base64
import binascii
import hashlib
import os
from pathlib import Path
import re
import select
import time

MAX_PAYLOAD = 524288
MAX_WIRE = MAX_PAYLOAD * 2 + 4096
NONCE = re.compile(r'[0-9a-f]{32}\Z')

class ProtocolError(ValueError):
    pass

def _nonce(value):
    if not NONCE.fullmatch(value):
        raise ProtocolError('Nonce must be exactly 32 lowercase hex digits')
    return value.encode('ascii')

def write_request(fd, verb, nonce, timeout=2):
    if verb not in ('PING', 'REPORT'):
        raise ProtocolError('Only PING and REPORT are permitted')
    data = verb.encode() + b' ' + _nonce(nonce) + b'\n'
    deadline = time.monotonic() + timeout
    while data:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise TimeoutError('Timed out sending diagnostic request')
        try:
            count = os.write(fd, data)
        except BlockingIOError:
            continue
        if count <= 0:
            raise ProtocolError('Serial port closed while sending request')
        data = data[count:]

def _read(fd, deadline, record):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Timed out waiting for diagnostic response')
    if not select.select([fd], [], [], min(remaining, 1))[0]:
        return b''
    try:
        data = os.read(fd, 65536)
    except BlockingIOError:
        return b''
    if not data:
        raise ProtocolError('Serial device disconnected')
    if record:
        record(data)
    return data

def handshake(fd, nonce, timeout=15, record=None):
    token = _nonce(nonce)
    expected = re.compile(rb'(?:^|\n)XOOM_READY_V2 ' + token + rb'\r?\n')
    deadline = time.monotonic() + timeout
    next_ping = 0
    buffer = bytearray()
    while time.monotonic() < deadline:
        if time.monotonic() >= next_ping:
            write_request(fd, 'PING', nonce)
            next_ping = time.monotonic() + 1
        buffer.extend(_read(fd, deadline, record))
        if expected.search(buffer):
            return
        if len(buffer) > 4096:
            raise ProtocolError('Unexpected unsolicited output; framed reporter not established')
    raise TimeoutError('Diagnostic readiness handshake timed out')

class FrameDecoder:
    def __init__(self, nonce):
        token = _nonce(nonce)
        self.nonce = nonce
        self.header = re.compile(rb'(?:^|\n)XOOM_REPORT_V2 ' + token + rb' ([0-9]{1,6}) ([0-9a-f]{64})\r?\n')
        self.end = re.compile(rb'(?:^|\n)XOOM_END_V2 ' + token + rb'\r?\n')
        self.error = re.compile(rb'(?:^|\n)XOOM_ERROR_V2 ' + token + rb' ([A-Z_]+)\r?\n')
        self.buffer = bytearray()
        self.payload = None

    def feed(self, data):
        if self.payload is not None:
            raise ProtocolError('Frame already completed')
        self.buffer.extend(data)
        if len(self.buffer) > MAX_WIRE:
            raise ProtocolError('Diagnostic wire-size limit exceeded')
        error = self.error.search(self.buffer)
        if error:
            raise ProtocolError('Device report error: ' + error[1].decode('ascii'))
        header = self.header.search(self.buffer)
        if not header:
            if len(self.buffer) > 4096:
                raise ProtocolError('No matching response header within prefix limit')
            return None
        size = int(header[1])
        if not 0 < size <= MAX_PAYLOAD:
            raise ProtocolError('Declared payload size is outside the permitted bound')
        end = self.end.search(self.buffer, header.end())
        if not end:
            return None
        body = self.buffer[header.end():end.start()]
        try:
            payload = base64.b64decode(b''.join(body.split()), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProtocolError('Invalid report base64') from exc
        if len(payload) != size:
            raise ProtocolError('Report byte count does not match header')
        if hashlib.sha256(payload).hexdigest().encode() != header[2]:
            raise ProtocolError('Report SHA-256 does not match header')
        nonce = self.nonce.encode()
        if not payload.startswith(b'XOOM_FRESH_REPORT_V2 ' + nonce + b'\n'):
            raise ProtocolError('Payload request identity is missing or stale')
        if not payload.endswith(b'XOOM_FRESH_REPORT_DONE ' + nonce + b'\n'):
            raise ProtocolError('Payload completion marker is missing')
        self.payload = payload
        return payload

def receive_report(fd, nonce, timeout=45, record=None):
    decoder = FrameDecoder(nonce)
    deadline = time.monotonic() + timeout
    while True:
        payload = decoder.feed(_read(fd, deadline, record))
        if payload is not None:
            return payload

def expected_geometry(path):
    lines = Path(path).read_text().splitlines()
    result = {}
    if len(lines) != 30:
        raise ProtocolError('Expected a complete ten-partition reference')
    for index in range(0, len(lines), 3):
        match = re.fullmatch(r'/sys/block/mmcblk0/(mmcblk0p(?:10|[1-9]))', lines[index])
        if not match or match[1] in result:
            raise ProtocolError('Invalid or duplicate reference partition')
        if not lines[index+1].isdigit() or not lines[index+2].isdigit():
            raise ProtocolError('Invalid reference geometry')
        result[match[1]] = (int(lines[index+1]), int(lines[index+2]))
    return result

def storage_result(payload, expected, disk_sectors=None):
    text = payload.decode('utf-8', errors='replace')
    mounts = re.search(r'^XOOM_MOUNTS_BEGIN\n(.*?)^XOOM_MOUNTS_END\n', text, re.M | re.S)
    if not mounts:
        raise ProtocolError('Mount-state evidence is missing')
    virtual = {'rootfs', 'proc', 'sysfs', 'devtmpfs', 'tmpfs', 'devpts', 'debugfs', 'pstore'}
    for line in mounts[1].splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[2] not in virtual:
            raise ProtocolError('Unexpected nonvirtual mount in diagnostic report')
    actual = {}
    for name, start, size in re.findall(r'^XOOM_PART (mmcblk0p[0-9]+) ([0-9]+) ([0-9]+)$', text, re.M):
        if name in actual:
            raise ProtocolError('Duplicate actual partition geometry')
        actual[name] = (int(start), int(size))
    disks = re.findall(r'^XOOM_DISK mmcblk0 ([0-9]+) ([01])$', text, re.M)
    if len(disks) > 1:
        raise ProtocolError('Duplicate disk geometry')
    result = {'state': 'not_discovered', 'android_filesystems_mounted': False,
              'actual': actual, 'missing': sorted(set(expected)-set(actual))}
    if not disks:
        return result
    sectors, ro = map(int, disks[0])
    result.update(disk_sectors=sectors, disk_read_only=bool(ro))
    if disk_sectors is not None and sectors != disk_sectors:
        result['state'] = 'disk_capacity_mismatch'
        return result
    if set(actual) != set(expected):
        result['state'] = 'partition_set_mismatch'
        return result
    extents = sorted(actual.values())
    if any(start < 0 or size <= 0 or start + size > sectors for start, size in extents):
        raise ProtocolError('Actual geometry is out of disk bounds')
    if any(a + size > b for (a, size), (b, _) in zip(extents, extents[1:])):
        raise ProtocolError('Actual partitions overlap')
    result['state'] = 'geometry_matches_reference' if actual == expected else 'geometry_mismatch'
    result['mismatches'] = {name: {'expected': expected[name], 'actual': actual[name]}
                            for name in expected if expected[name] != actual[name]}
    return result
