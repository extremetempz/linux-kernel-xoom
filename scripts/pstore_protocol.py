"""Bounded read-only PSTORE framing, separate from normal REPORT limits."""
import base64
import binascii
import hashlib
import re
from diagnostic_protocol import ProtocolError

MAX_PSTORE_PAYLOAD = 2097152
MAX_PSTORE_WIRE = 3145728

def extract_pstore_frame(data, nonce):
    if not re.fullmatch(r'[0-9a-f]{32}', nonce):
        raise ProtocolError('Invalid PSTORE nonce')
    if len(data) > MAX_PSTORE_WIRE:
        raise ProtocolError('PSTORE response too large')
    token = nonce.encode()
    error = re.search(rb'(?:^|\n)XOOM_ERROR_V2 ' + token + rb' ([A-Z_]+)\r?\n', data)
    if error:
        raise ProtocolError('Device PSTORE error: ' + error[1].decode())
    header = re.search(rb'(?:^|\n)XOOM_PSTORE_V1 ' + token + rb' ([0-9]{1,7}) ([0-9a-f]{64})\r?\n', data)
    if not header:
        return None
    size = int(header[1])
    if not 0 < size <= MAX_PSTORE_PAYLOAD:
        raise ProtocolError('Invalid PSTORE size')
    end = re.search(rb'(?:^|\n)XOOM_PSTORE_END_V1 ' + token + rb'\r?\n', data[header.end():])
    if not end:
        return None
    try:
        payload = base64.b64decode(b''.join(data[header.end():header.end()+end.start()].split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ProtocolError('Invalid PSTORE base64') from exc
    if len(payload) != size or hashlib.sha256(payload).hexdigest().encode() != header[2]:
        raise ProtocolError('PSTORE size/hash mismatch')
    if not payload.startswith(b'XOOM_PSTORE_REPORT_V1\n') or not payload.endswith(b'XOOM_PSTORE_REPORT_END\n'):
        raise ProtocolError('PSTORE payload markers missing')
    return payload
