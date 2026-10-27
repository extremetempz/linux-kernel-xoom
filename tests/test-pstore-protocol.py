#!/usr/bin/env python3
"""Large retained-log frames must fit; reject corrupt/oversized responses."""
from pathlib import Path
import base64
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pstore_protocol import extract_pstore_frame, MAX_PSTORE_PAYLOAD, MAX_PSTORE_WIRE
from diagnostic_protocol import ProtocolError, MAX_PAYLOAD

nonce = 'a' * 32
def frame(payload, token=nonce):
    return (f'XOOM_PSTORE_V1 {token} {len(payload)} {hashlib.sha256(payload).hexdigest()}\n'.encode()
            + base64.encodebytes(payload) + f'\nXOOM_PSTORE_END_V1 {token}\n'.encode())
start, end = b'XOOM_PSTORE_REPORT_V1\n', b'XOOM_PSTORE_REPORT_END\n'
for size in (64, 524288, 1048576, MAX_PSTORE_PAYLOAD):
    payload = start + b'x' * (size - len(start) - len(end)) + end
    wire = frame(payload)
    assert len(wire) <= MAX_PSTORE_WIRE
    assert extract_pstore_frame(wire[:len(wire)//2], nonce) is None
    assert extract_pstore_frame(wire, nonce) == payload
assert extract_pstore_frame(frame(start + end, 'b'*32), nonce) is None
assert MAX_PAYLOAD == 524288  # Normal REPORT limit is unchanged.
bad = [
    frame(b'bad markers'),
    frame(start + end).replace(hashlib.sha256(start + end).hexdigest().encode(), b'0'*64),
    frame(start + end).replace(base64.encodebytes(start + end), b'%%%\n'),
    f'XOOM_PSTORE_V1 {nonce} {MAX_PSTORE_PAYLOAD+1} '.encode() + b'0'*64+b'\n',
    b'x'*(MAX_PSTORE_WIRE+1),
    f'XOOM_ERROR_V2 {nonce} PSTORE_FAILED\n'.encode(),
]
for wire in bad:
    try:
        extract_pstore_frame(wire, nonce)
    except ProtocolError:
        pass
    else:
        raise AssertionError('Accepted invalid frame')
print('PASS 2MiB raw / base64 wire bounds, partial frames, nonce/hash/size/encoding errors; normal REPORT cap unchanged')
