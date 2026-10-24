#!/usr/bin/env python3
"""Verify a compiled host-only diagnostic kernel; never accesses a device."""
import sys
from host_test import validate_artifacts
if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('Usage: verify-host-test.py ARTIFACT_DIRECTORY')
    validate_artifacts(sys.argv[1])
    print('PASS host-only diagnostic: exact board delta, original allocator reservation, firmware host rate policy; GPU/DC/EMC/DVFS disabled. Hardware execution pending.')
