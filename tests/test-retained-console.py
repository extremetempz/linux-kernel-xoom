#!/usr/bin/env python3
"""Compiled memory ownership gates and negative controls; no hardware claim."""
from pathlib import Path
import copy
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from retained_console_profile import (validate_retained_console_artifacts,
    validate_trees, validate_ecc_tree, selected_retained_dt, ECC_DT)
from legacy_resources import parse_dtb
from wakeirq_profile import validate_wakeirq_artifacts
p = Path(sys.argv[1])
validate_wakeirq_artifacts(p, require_dc=False)
validate_retained_console_artifacts(p)
a = parse_dtb((p / 'tegra20-motorola-wingray-android44-wakeirq.dtb').read_bytes())
b = parse_dtb((p / 'tegra20-motorola-wingray-android44-wakeirqtrace.dtb').read_bytes())
for mutation in ('missing_phandle', 'wrong_phandle', 'overlap', 'size', 'no_map', 'layout'):
    c = copy.deepcopy(b)
    if mutation == 'missing_phandle':
        del c['/ramoops@1ff00000']['memory-region']
    elif mutation == 'wrong_phandle':
        c['/ramoops@1ff00000']['memory-region'] = struct.pack('>I', 0xffff)
    elif mutation == 'overlap':
        c['/reserved-memory/legacy-console@1fe00000']['reg'] = struct.pack('>II', 0x1fe00000, 0x200000)
    elif mutation == 'size':
        c['/reserved-memory/ramoops@1ff00000']['reg'] = struct.pack('>II', 0x1ff00000, 0x200000)
    elif mutation == 'no_map':
        del c['/reserved-memory/ramoops@1ff00000']['no-map']
    else:
        c['/ramoops@1ff00000']['console-size'] = struct.pack('>Q', 0x100000)
    try:
        validate_trees(a, c)
    except (AssertionError, KeyError):
        pass
    else:
        raise AssertionError('Accepted ' + mutation)
init = (ROOT / 'diagnostic/android44-init.sh').read_text()
assert 'if [ -e /proc/device-tree/motorola,wingray-pstore-test ]; then' in init
assert 'mount -t pstore -o ro,nosuid,nodev,noexec' in init
assert 'XOOM_PSTORE_BOOT' in init
if selected_retained_dt((p / 'kernel.config').read_text()) == ECC_DT:
    ecc = parse_dtb((p / (ECC_DT + '.dtb')).read_bytes())
    for mutation in ('ecc_missing', 'ecc_wrong', 'ecc_u64', 'no_marker', 'dc_wiring', 'reservation'):
        c = copy.deepcopy(ecc)
        if mutation == 'ecc_missing':
            del c['/ramoops@1ff00000']['ecc-size']
        elif mutation == 'ecc_wrong':
            c['/ramoops@1ff00000']['ecc-size'] = struct.pack('>I', 32)
        elif mutation == 'ecc_u64':
            c['/ramoops@1ff00000']['ecc-size'] = struct.pack('>Q', 16)
        elif mutation == 'no_marker':
            del c['/']['motorola,wingray-pstore-ecc-test']
        elif mutation == 'dc_wiring':
            c['/host1x@50000000/dc@54200000']['status'] = b'disabled\0'
        else:
            c['/reserved-memory/ramoops@1ff00000']['reg'] = struct.pack('>II', 0x20000000, 0x100000)
        try:
            validate_ecc_tree(b, c)
        except (AssertionError, KeyError):
            pass
        else:
            raise AssertionError('Accepted ' + mutation)
print('PASS compiled phandle/partitions, unchanged reservation union, no overlap, guarded read-only mount; retention hardware-unverified')
