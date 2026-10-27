#!/usr/bin/env python3
"""Check compiled IRQ-test DT/config and reject sleep or wiring drift."""
from pathlib import Path
import shutil
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from wakeirq_profile import validate_wakeirq_artifacts

p = Path(sys.argv[1])
validate_wakeirq_artifacts(p)
with tempfile.TemporaryDirectory() as directory:
    q = Path(directory)
    for name in ('kernel.config', 'tegra20-motorola-wingray-android44-displaypm.dtb',
                 'tegra20-motorola-wingray-android44-wakeirq.dtb'):
        shutil.copyfile(p / name, q / name)
    original = (q / 'kernel.config').read_text()
    for option in ('PM', 'SUSPEND', 'CPU_FREQ', 'REGULATOR_CPCAP'):
        (q / 'kernel.config').write_text(original + '\nCONFIG_' + option + '=y\n')
        try:
            validate_wakeirq_artifacts(q)
        except AssertionError:
            pass
        else:
            raise AssertionError('Accepted forbidden ' + option)
    for option in ('MFD_CPCAP_WINGRAY_IRQ_TEST', 'FB_TEGRA_WINGRAY_DC_RESUME_TEST'):
        (q / 'kernel.config').write_text(original.replace('CONFIG_' + option + '=y\n', ''))
        try:
            validate_wakeirq_artifacts(q)
        except AssertionError:
            pass
        else:
            raise AssertionError('Accepted missing patch/config ' + option)
    (q / 'kernel.config').write_text(original)
    data = (q / 'tegra20-motorola-wingray-android44-wakeirq.dtb').read_bytes()
    # The 10 MHz CPCAP SPI limit occurs exactly once in this tree. Keep the
    # binary valid while checking that a transport change is rejected.
    old, new = struct.pack('>I', 10000000), struct.pack('>I', 10000001)
    assert data.count(old) == 1
    (q / 'tegra20-motorola-wingray-android44-wakeirq.dtb').write_bytes(data.replace(old, new))
    try:
        validate_wakeirq_artifacts(q)
    except AssertionError:
        pass
    else:
        raise AssertionError('Accepted changed SPI transport')

builder = (ROOT / 'scripts/build-android-gpu.sh').read_text()
assert "grep -qx 'CONFIG_MFD_CPCAP_WINGRAY_IRQ_TEST=y'" in builder
assert "grep -qx 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y'" in builder
print('PASS compiled IRQ-only scope, same physical IRQ/polarity, unchanged SPI/rails/graphics/radios, missing-patch and forbidden-PM negative controls')
