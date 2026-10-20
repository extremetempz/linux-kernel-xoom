#!/usr/bin/env python3
"""Verify built ARM image, appended DTB, actual board wiring and config gates."""
from pathlib import Path
import struct
import sys

artifacts = Path(sys.argv[1])
profile = sys.argv[2] if len(sys.argv) > 2 else 'peripherals'
assert profile in ('early', 'trace', 'peripherals', 'diagnostic')
image = (artifacts / 'zImage').read_bytes()
dtname = ('tegra20-motorola-wingray-diagnostic' if profile == 'diagnostic' else
          'tegra20-motorola-wingray-early' if profile in ('early', 'trace') else 'tegra20-motorola-wingray')
dtb = (artifacts / (dtname + '.dtb')).read_bytes()
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
if profile == 'diagnostic':
    config = (artifacts / 'kernel.config').read_text().splitlines()
    for option in ['SMP', 'CACHE_L2X0', 'DEBUG_LL', 'DEBUG_UNCOMPRESS', 'NET',
                   'INPUT', 'DRM', 'MFD_CPCAP', 'REGULATOR_MAX8649', 'BRCMFMAC',
                   'CPU_FREQ', 'CPU_IDLE', 'SUSPEND']:
        assert f'CONFIG_{option}=y' not in config and f'CONFIG_{option}=m' not in config, option
    for option in ['ARM_APPENDED_DTB', 'ARM_ATAG_DTB_COMPAT', 'PSTORE_RAM',
                   'MOTOROLA_XOOM_BOOT_TRACE', 'MOTOROLA_XOOM_BIGPART',
                   'MMC_BLOCK', 'MMC_SDHCI_TEGRA', 'USB_CHIPIDEA_UDC',
                   'USB_G_SERIAL', 'USB_TEGRA_PHY', 'USB_PHY', 'USB_ULPI_VIEWPORT',
                   'SWP_EMULATE', 'DEVTMPFS', 'BINFMT_ELF', 'BINFMT_SCRIPT']:
        assert f'CONFIG_{option}=y' in config, option
    for node in ['/sdhci@c8000600', '/usb@c5000000', '/usb-phy@c5000000']:
        assert nodes[node]['status'] == b'okay\0', node
    assert nodes['/host1x@50000000']['status'] == b'disabled\0'
    assert nodes['/usb@c5000000']['compatible'] == b'nvidia,tegra20-udc\0'
    assert nodes['/usb-phy@c5000000']['dr_mode'] == b'peripheral\0'
    assert 'motorola,xoom-bigpart' in nodes['/sdhci@c8000600']
    assert '/panel' not in nodes and '/i2c@7000c000/touchscreen@5b' not in nodes
    for node in ['/gpio@6000d000/usb-data-enable', '/gpio@6000d000/usb-forceon-n']:
        assert 'gpio-hog' in nodes[node] and 'output-high' in nodes[node]
    for name, region in [('/reserved-memory/legacy-video@2e800000', (0x2e800000, 0x11800000)),
                         ('/reserved-memory/legacy-console@1fe00000', (0x1fe00000, 0x200000))]:
        assert struct.unpack('>II', nodes[name]['reg']) == region and 'no-map' in nodes[name]
    assert not any('earlycon=' in line or 'earlyprintk' in line for line in config if line.startswith('CONFIG_CMDLINE='))
    symbols = (artifacts / 'System.map').read_text().splitlines()
    names = {line.split()[-1] for line in symbols if len(line.split()) == 3}
    for name in ['tegra_usb_phy_probe', 'tegra_udc_probe', 'devm_usb_get_phy_by_phandle']:
        assert name in names, 'Missing actual USB PHY implementation: ' + name
    print('Verified diagnostic profile: UP, fixed reservations, USB peripheral/serial and BigPart eMMC, no display/network/input probes.')
    sys.exit(0)
if profile in ('early', 'trace'):
    config = (artifacts / 'kernel.config').read_text().splitlines()
    for option in ['SMP', 'CACHE_L2X0', 'DEBUG_LL', 'DEBUG_UNCOMPRESS', 'BLOCK',
                   'MMC', 'USB', 'DRM', 'MFD_CPCAP', 'REGULATOR_MAX8649', 'BRCMFMAC']:
        assert f'CONFIG_{option}=y' not in config and f'CONFIG_{option}=m' not in config, option
    for node in ['/host1x@50000000', '/sdhci@c8000600', '/usb@c5000000', '/usb-phy@c5000000']:
        assert nodes[node]['status'] == b'disabled\0', node
    assert '/panel' not in nodes and '/i2c@7000c000/touchscreen@5b' not in nodes
    for option in ['ARM_APPENDED_DTB', 'ARM_ATAG_DTB_COMPAT', 'PSTORE_RAM', 'SERIAL_8250_CONSOLE']:
        assert f'CONFIG_{option}=y' in config, option
    assert not any('earlycon=' in line or 'earlyprintk' in line for line in config if line.startswith('CONFIG_CMDLINE='))
    assert (f'CONFIG_MOTOROLA_XOOM_BOOT_TRACE=y' in config) == (profile == 'trace')
    print('Verified early profile: ARM/DTB/memory handoff, UP, no L2 driver, no pre-console UART polling or peripheral probes.')
    sys.exit(0)
emmc = nodes['/sdhci@c8000600']
assert emmc['status'] == b'okay\0' and 'motorola,xoom-bigpart' in emmc
assert struct.unpack('>I', emmc['bus-width'])[0] == 8
assert nodes['/host1x@50000000']['status'] == b'okay\0'
assert nodes['/usb@c5000000']['compatible'] == b'nvidia,tegra20-udc\0'
assert nodes['/usb-phy@c5000000']['dr_mode'] == b'peripheral\0'
# Board-specific peripheral wiring must survive DT compilation.
assert nodes['/panel']['compatible'] == b'motorola,wingray-auo-panel\0'
assert nodes['/i2c@7000c000/backlight@2c']['compatible'] == b'ti,lp8550\0'
touch = nodes['/i2c@7000c000/touchscreen@5b']
assert touch['compatible'].split(b'\0')[0] == b'motorola,wingray-maxtouch'
assert struct.unpack('>II', touch['interrupts']) == (170, 8), 'P3 touch IRQ must be PV2, level-low'
assert nodes['/sdhci@c8000200']['status'] == b'okay\0'
assert nodes['/sdhci@c8000200/wifi@1']['compatible'] == b'brcm,bcm4329-fmac\0'
assert struct.unpack('>I', nodes['/sdhci@c8000200']['nvidia,tap-delay'])[0] == 6
config = (artifacts / 'kernel.config').read_text().splitlines()
for option in ['MACH_MOTOROLA_WINGRAY', 'MOTOROLA_XOOM_BIGPART', 'MMC_SDHCI_TEGRA',
               'ARM_APPENDED_DTB', 'ARM_ATAG_DTB_COMPAT', 'USB_CHIPIDEA_UDC', 'USB_G_SERIAL', 'USB_TEGRA_PHY', 'USB_PHY', 'PSTORE_RAM', 'MFD_CPCAP', 'REGULATOR_CPCAP', 'REGULATOR_MAX8649',
               'DRM_TEGRA', 'DRM_PANEL_SIMPLE', 'TOUCHSCREEN_ATMEL_MXT', 'BACKLIGHT_LP855X', 'BRCMFMAC',
               'BRCMFMAC_SDIO', 'POWER_RESET_WINGRAY', 'DMA_CMA']:
    assert f'CONFIG_{option}=y' in config, option
for option in ['NEON', 'CPU_FREQ', 'CPU_IDLE', 'SUSPEND', 'BIGSYS', 'MACH_SAMSUNG_P4WIFI', 'TEGRA_DOWNSTREAM']:
    assert f'CONFIG_{option}=y' not in config and f'CONFIG_{option}=m' not in config, option
print('Verified ARM image, appended Wingray DTB, memory, eMMC/BigPart, USB and configuration gates.')
