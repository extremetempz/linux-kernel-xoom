#!/usr/bin/env python3
"""Static checks for the Bluetooth Android preparation handoff."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
setup = (ROOT / 'diagnostic/bluetooth-setup.sh').read_text()
rc = (ROOT / 'scripts/prepare-android-gpu.py').read_text()

for needle in (
    'while [ "$attempt" -le 60 ]',
    '/sys/class/rfkill/rfkill*',
    "= 'bcm4329 Bluetooth'",
    '/dev/ttyHS2',
    '/system/lib/hw/bluetooth.default.so',
    '/system/etc/firmware/bcm4329.hcd',
    '/system/lib/libbt-vendor.so',
    '/system/vendor/lib/libbt-vendor.so',
    'rfkill_path/state',
    'READY_for_manual_Android_Bluetooth_toggle_NOT_hardware_validated',
):
    assert needle in setup, needle
assert 'on property:sys.boot_completed=1' in rc
assert 'start xoombtsetup' in rc
print('PASS Bluetooth setup waits for UART, rfkill, HAL and firmware; boot-completed retry present')
