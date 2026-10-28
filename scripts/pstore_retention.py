"""Strict offline warm-reset evidence checks. Never opens a device."""
import hashlib
import json
from pathlib import Path
import re

from diagnostic_protocol import ProtocolError
from pstore_protocol import extract_pstore_frame, MAX_PSTORE_PAYLOAD

UUID = rb'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
PARAMS = {'mem_address': 0x1ff00000, 'mem_size': 0x100000,
          'record_size': 0x20000, 'console_size': 0x80000, 'pmsg_size': 0x20000}


def require(condition, reason):
    if not condition:
        raise ProtocolError(reason)


def load_capture(directory):
    """Recheck original wire framing/hash instead of trusting an edited log."""
    p = Path(directory)
    status = json.loads((p / 'status.json').read_text())
    require(status.get('state') == 'verified' and status.get('request') == 'PSTORE',
            'Capture did not complete a verified PSTORE request')
    wire_path = p / 'wire-private.bin'
    # Bound reads as well as the decoder's allocation, even for local fixtures.
    with wire_path.open('rb') as stream:
        wire = stream.read(3145729)
    payload = extract_pstore_frame(wire, status.get('nonce', ''))
    require(payload is not None, 'Incomplete PSTORE wire frame')
    with (p / 'pstore-report.txt').open('rb') as stream:
        saved = stream.read(MAX_PSTORE_PAYLOAD + 1)
    require(saved == payload, 'Saved payload differs from verified wire frame')
    require(status.get('bytes') == len(payload) and
            status.get('sha256') == hashlib.sha256(payload).hexdigest(),
            'Capture status size/hash disagrees with verified wire frame')
    return parse_report(payload)


def parse_report(payload):
    require(0 < len(payload) <= MAX_PSTORE_PAYLOAD, 'Invalid report length')
    require(payload.startswith(b'XOOM_PSTORE_REPORT_V1\n') and
            payload.endswith(b'XOOM_PSTORE_REPORT_END\n'), 'Missing report markers')
    header, separator, rest = payload.partition(b'PSTORE_DIR\n')
    require(bool(separator), 'Missing pstore directory section')
    ids = re.findall(rb'^CURRENT_BOOT_ID (' + UUID + rb')$', header, re.M)
    require(len(ids) == 1, 'Missing or invalid current boot UUID')
    require(b'PSTORE_MOUNTED_yes\n' in header and b'PSTORE_MOUNT_RC 0\n' in header,
            'Pstore mount not confirmed')
    require(b'RAMOOPS_BOUND /sys/bus/platform/drivers/ramoops/1ff00000.ramoops\n' in header,
            'Ramoops backend binding not confirmed')
    for name, value in PARAMS.items():
        matches = re.findall(rb'^RAMOOPS_PARAM ' + name.encode() + rb' ([0-9]+)$', header, re.M)
        require(matches == [str(value).encode()], 'Ramoops layout mismatch: ' + name)
    records = {}
    cursor = 0
    while True:
        match = re.search(rb'(?:^|\n)PSTORE_FILE /sys/fs/pstore/([a-z0-9-]+)\n'
                          rb'PSTORE_BYTES original=([0-9]+) captured=([0-9]+)\n', rest[cursor:])
        if match is None:
            break
        name = match[1].decode()
        size, captured = int(match[2]), int(match[3])
        require(size == captured and 0 < captured <= MAX_PSTORE_PAYLOAD,
                'Truncated or invalid retained record')
        start = cursor + match.end()
        end = start + captured
        require(rest[end:].startswith(b'PSTORE_FILE_END\n'), 'Retained record length mismatch')
        require(name not in records, 'Duplicate retained record')
        records[name] = rest[start:end]
        cursor = end + len(b'PSTORE_FILE_END\n')
    # Truncation notices outside file bodies invalidate a complete capture.
    require(b'PSTORE_TRUNCATED_' not in rest[cursor:], 'Pstore file capture was truncated')
    probes = re.findall(rb'^PSTORE_CURRENT_PROBE_BEGIN\n([^\n]*)\nPSTORE_CURRENT_PROBE_END$', header, re.M)
    return {'boot_id': ids[0], 'header': header, 'records': records,
            'probe': probes[0] if len(probes) == 1 else None}


def validate_probe(probe, boot_id):
    require(probe is not None, 'Missing ECC-profile current retention probe')
    prefix = b'XOOM_PSTORE_PROBE_V1 ' + boot_id + b' '
    pattern = b'0123456789abcdef' * 16
    digest = hashlib.sha256(boot_id + b' ' + pattern).hexdigest().encode()
    require(probe == prefix + pattern + b' ' + digest,
            'Current retention probe content/hash mismatch')


def compare_retention(before, after):
    old_id, new_id = before['boot_id'], after['boot_id']
    require(old_id != new_id, 'Same boot: a second capture is not a warm-reset test')
    console = after['records'].get('console-ramoops-0', b'')
    require(bool(console), 'Previous console missing')
    # Search ONLY old console bytes, never the current dmesg tail or pmsg.
    require(re.search(rb'XOOM_PSTORE_BOOT ' + re.escape(old_id) + rb' mount_rc=0(?:\r?\n|$)', console),
            'Previous boot marker missing or corrupted in old console')
    require(not re.search(rb'XOOM_PSTORE_BOOT ' + re.escape(new_id) + rb' ', console),
            'Current boot marker found in purported previous console')
    for report in (before, after):
        require(b'RAMOOPS_DT_ECC_HEX 00000010\n' in report['header'],
                'Both captures must use the same ECC-16 profile')
        validate_probe(report['probe'], report['boot_id'])
    old_probe = before['probe']
    require(console.count(old_probe + b'\n') == 1,
            'Previous multi-block probe missing, duplicated or corrupted')
    # The kernel appends this notice after the saved ring. It describes ECC
    # recovery, not a guarantee about all bytes or the electrical reset cause.
    if console.endswith(b'\nNo errors detected\n'):
        corrected = 0
    else:
        ecc = re.search(rb'\n([0-9]+) Corrected bytes, ([0-9]+) unrecoverable blocks\n$', console)
        require(ecc is not None, 'ECC recovery status missing')
        require(int(ecc[2]) == 0, 'ECC reports unrecoverable console blocks')
        corrected = int(ecc[1])
    return {'gate_passed': True, 'previous_boot_id': old_id.decode(),
            'current_boot_id': new_id.decode(), 'console_bytes': len(console),
            'probe_bytes': len(old_probe), 'ecc_corrected_bytes': corrected,
            'ecc_unrecoverable_blocks': 0,
            'scope': 'Exact known console probe across one warm reset; not whole-log integrity or suspend validation'}
