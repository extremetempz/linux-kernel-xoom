#!/usr/bin/env python3
"""Verify two saved PSTORE captures offline; does not flash, reset or suspend."""
import argparse
import json
from pstore_retention import load_capture, compare_retention
from diagnostic_protocol import ProtocolError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, help='First private PSTORE capture directory')
    parser.add_argument('--after', required=True, help='Capture after a manual warm reset into the same ECC image')
    args = parser.parse_args()
    try:
        result = compare_retention(load_capture(args.before), load_capture(args.after))
    except (ProtocolError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'gate_passed': False, 'reason': str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
