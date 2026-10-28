#!/usr/bin/env python3
"""Fail closed on corrupt/stale/partial saved reset evidence; no devices."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from diagnostic_protocol import ProtocolError
from pstore_retention import parse_report, compare_retention, load_capture, PARAMS

OLD = b'5a938e4d-83e4-4bdb-a8c5-1370ef46fa72'
NEW = b'64f4ed82-2568-4b16-8f43-c484eefb94bd'
NONCE = '0123456789abcdef' * 2


def probe(boot):
    pattern = b'0123456789abcdef' * 16
    digest = hashlib.sha256(boot + b' ' + pattern).hexdigest().encode()
    return b'XOOM_PSTORE_PROBE_V1 ' + boot + b' ' + pattern + b' ' + digest


def console(boot=OLD, footer=b'\nNo errors detected\n'):
    return (b'[ 2.4] XOOM_PSTORE_BOOT ' + boot + b' mount_rc=0\n'
            b'[ 2.5] ' + probe(boot) + b'\n' + footer)


def report(boot, old=None):
    header = (b'XOOM_PSTORE_REPORT_V1\nCURRENT_BOOT_ID ' + boot + b'\n'
              b'PSTORE_CURRENT_PROBE_BEGIN\n' + probe(boot) + b'\nPSTORE_CURRENT_PROBE_END\n'
              b'RAMOOPS_DT_ECC_HEX 00000010\nPSTORE_MOUNTED_yes\nPSTORE_MOUNT_RC 0\n'
              b'RAMOOPS_BOUND /sys/bus/platform/drivers/ramoops/1ff00000.ramoops\n')
    header += b''.join(b'RAMOOPS_PARAM ' + n.encode() + b' ' + str(v).encode() + b'\n' for n, v in PARAMS.items())
    header += b'PSTORE_DIR\n'
    if old is not None:
        header += (b'PSTORE_FILE /sys/fs/pstore/console-ramoops-0\n'
                   + f'PSTORE_BYTES original={len(old)} captured={len(old)}\n'.encode()
                   + old + b'PSTORE_FILE_END\n')
    return header + b'DMESG_TAIL\n[ 2.5] ' + probe(boot) + b'\nXOOM_PSTORE_REPORT_END\n'


def capture(directory, payload):
    digest = hashlib.sha256(payload).hexdigest()
    wire = (f'XOOM_PSTORE_V1 {NONCE} {len(payload)} {digest}\n'.encode() +
            base64.encodebytes(payload) + f'\nXOOM_PSTORE_END_V1 {NONCE}\n'.encode())
    directory.mkdir()
    (directory / 'wire-private.bin').write_bytes(wire)
    (directory / 'pstore-report.txt').write_bytes(payload)
    (directory / 'status.json').write_text(json.dumps({'state': 'verified', 'request': 'PSTORE',
                    'nonce': NONCE, 'bytes': len(payload), 'sha256': digest}))


class Retention(unittest.TestCase):
    def compare(self, payload=None, before=None):
        return compare_retention(parse_report(before or report(OLD)),
                                 parse_report(payload or report(NEW, console())))

    def test_clean_and_corrected_probe(self):
        result = self.compare()
        self.assertTrue(result['gate_passed'])
        self.assertEqual(result['ecc_corrected_bytes'], 0)
        corrected = console(footer=b'\n1 Corrected bytes, 0 unrecoverable blocks\n')
        self.assertEqual(self.compare(report(NEW, corrected))['ecc_corrected_bytes'], 1)

    def test_observed_single_bit_corruption_is_rejected(self):
        damaged = console().replace(b'5a938e4d', b'5a9s8e4d', 1)
        with self.assertRaisesRegex(ProtocolError, 'marker missing or corrupted'):
            self.compare(report(NEW, damaged))

    def test_probe_damage_not_hidden_by_valid_uuid(self):
        damaged = console().replace(probe(OLD), probe(OLD).replace(b'0123', b'01s3', 1))
        with self.assertRaisesRegex(ProtocolError, 'multi-block probe'):
            self.compare(report(NEW, damaged))

    def test_same_boot_current_log_and_missing_console(self):
        for value in (report(OLD, console()), report(NEW, console(NEW)), report(NEW)):
            with self.assertRaises(ProtocolError):
                self.compare(value)
        # Exact previous markers in the CURRENT tail cannot substitute for an old record.
        bad = report(NEW, b'no previous marker\nNo errors detected\n').replace(b'DMESG_TAIL\n', b'DMESG_TAIL\n' + console())
        with self.assertRaises(ProtocolError):
            self.compare(bad)

    def test_reject_bad_or_missing_ecc_status(self):
        for footer in (b'', b'\n1 Corrected bytes, 1 unrecoverable blocks\n'):
            with self.assertRaises(ProtocolError):
                self.compare(report(NEW, console(footer=footer)))
        with self.assertRaises(ProtocolError):
            self.compare(report(NEW, console()).replace(b'00000010', b'absent'))

    def test_wrong_layout_mount_backend_probe_and_truncation(self):
        data = report(NEW, console())
        variants = [data.replace(b'PSTORE_MOUNTED_yes', b'PSTORE_MOUNTED_no'),
                    data.replace(b'RAMOOPS_BOUND ', b'RAMOOPS_BACKEND_UNBOUND '),
                    data.replace(b'mem_size 1048576', b'mem_size 2097152'),
                    data.replace(probe(NEW), probe(NEW)[:-1] + b'x', 1),
                    data.replace(b'PSTORE_BYTES original=', b'PSTORE_BYTES original=1'),
                    data.replace(b'PSTORE_FILE_END\n', b'PSTORE_TRUNCATED_TAIL\n'),
                    data.replace(b'DMESG_TAIL', b'PSTORE_TRUNCATED_FILE_COUNT\nDMESG_TAIL')]
        for value in variants:
            with self.subTest(value=value[-100:]), self.assertRaises(ProtocolError):
                self.compare(value)

    def test_binary_record_markers_are_not_reparsed_as_metadata(self):
        old = console(footer=b'') + b'PSTORE_FILE_END\nDMESG_TAIL\n\x00\xff\nNo errors detected\n'
        self.assertTrue(self.compare(report(NEW, old))['gate_passed'])

    def test_wire_saved_status_integrity_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = root / 'before', root / 'after'
            capture(before, report(OLD)); capture(after, report(NEW, console()))
            self.assertTrue(compare_retention(load_capture(before), load_capture(after))['gate_passed'])
            command = [sys.executable, str(ROOT/'scripts/check-pstore-retention.py'), '--before', str(before), '--after', str(after)]
            result = subprocess.run(command, check=True, capture_output=True)
            self.assertTrue(json.loads(result.stdout)['gate_passed'])
            path = after / 'pstore-report.txt'
            original = path.read_bytes(); path.write_bytes(original.replace(b'00000010', b'00000011'))
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('verified wire', json.loads(result.stdout)['reason'])
            path.write_bytes(original)
            status = json.loads((after/'status.json').read_text()); status['sha256'] = '0'*64
            (after/'status.json').write_text(json.dumps(status))
            with self.assertRaises(ProtocolError):
                load_capture(after)
            status['sha256'] = hashlib.sha256(original).hexdigest()
            (after/'status.json').write_text(json.dumps(status))
            wire = after/'wire-private.bin'; wire.write_bytes(wire.read_bytes().replace(base64.encodebytes(original)[:16], b'x'*16, 1))
            with self.assertRaises(ProtocolError):
                load_capture(after)


if __name__ == '__main__':
    unittest.main()
