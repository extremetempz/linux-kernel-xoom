#!/usr/bin/env python3
"""Verify built ARM image, appended DTB, actual board wiring and config gates."""
from pathlib import Path
import struct
import sys

artifacts = Path(sys.argv[1])
image = (artifacts / 'zImage').read_bytes()
dtb = (artifacts / 'tegra20-motorola-wingray.dtb').read_bytes()
assert struct.unpack_from('<I', image, 36)[0] == 0x016F2818, 'Invalid ARM zImage magic'
assert (artifacts / 'zImage-dtb').read_bytes() == image + dtb, 'Appended DTB mismatch'
magic, total, off_struct, off_strings = struct.unpack_from('>4I', dtb)
assert magic == 0xD00DFEED and total == len(dtb), 'Invalid DTB header'
nodes, stack = {}, []
cursor = off_struct
while True:
    token = struct.unpack_from('>I', dtb, cursor)[0]
    cursor += 4
    if token == 1:
        end = dtb.index(b'\0', cursor)
        stack.append(dtb[cursor:end].decode())
        cursor = (end + 4) & ~3
        nodes.setdefault('/'.join(stack) or '/', {})
    elif token == 2:
        stack.pop()
    elif token == 3:
        length, nameoff = struct.unpack_from('>II', dtb, cursor)
        cursor += 8
        start = off_strings + nameoff
        name = dtb[start:dtb.index(b'\0', start)].decode()
        nodes['/'.join(stack) or '/'][name] = dtb[cursor:cursor + length]
        cursor = (cursor + length + 3) & ~3
    elif token == 4:
        pass
    elif token == 9:
        break
    else:
        raise AssertionError(f'Invalid DTB token {token}')
assert nodes['/']['compatible'].split(b'\0')[:2] == [b'motorola,wingray', b'nvidia,tegra20']
memories = [n for n, p in nodes.items() if p.get('device_type') == b'memory\0']
assert memories == ['/memory'], 'Duplicate memory nodes could corrupt ATAG fixups'
assert struct.unpack('>II', nodes['/memory']['reg']) == (0, 0x40000000)
emmc = nodes['/sdhci@c8000600']
assert emmc['status'] == b'okay\0' and 'motorola,xoom-bigpart' in emmc
assert struct.unpack('>I', emmc['bus-width'])[0] == 8
assert nodes['/host1x@50000000']['status'] == b'disabled\0'
assert nodes['/usb@c5000000']['compatible'] == b'nvidia,tegra20-udc\0'
assert nodes['/usb-phy@c5000000']['dr_mode'] == b'peripheral\0'
config = (artifacts / 'kernel.config').read_text().splitlines()
for option in ['MACH_MOTOROLA_WINGRAY', 'MOTOROLA_XOOM_BIGPART', 'MMC_SDHCI_TEGRA',
               'ARM_APPENDED_DTB', 'ARM_ATAG_DTB_COMPAT', 'USB_CHIPIDEA_UDC', 'USB_G_SERIAL', 'PSTORE_RAM']:
    assert f'CONFIG_{option}=y' in config, option
for option in ['NEON', 'CPU_FREQ', 'CPU_IDLE', 'SUSPEND', 'BIGSYS', 'MACH_SAMSUNG_P4WIFI', 'TEGRA_DOWNSTREAM']:
    assert f'CONFIG_{option}=y' not in config and f'CONFIG_{option}=m' not in config, option
print('Verified ARM image, appended Wingray DTB, memory, eMMC/BigPart, USB and configuration gates.')
