#!/usr/bin/env python3
"""Verify built ARM image, appended DTB, actual board wiring and config gates."""
from pathlib import Path
import struct
import sys

artifacts = Path(sys.argv[1])
profile = sys.argv[2] if len(sys.argv) > 2 else 'peripherals'
assert profile in ('early', 'trace', 'peripherals', 'diagnostic', 'panelbus', 'display')
image = (artifacts / 'zImage').read_bytes()
dtname = ('tegra20-motorola-wingray-display' if profile == 'display' else
          'tegra20-motorola-wingray-panelbus' if profile == 'panelbus' else
          'tegra20-motorola-wingray-diagnostic' if profile == 'diagnostic' else
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
# GPIO hogs run before the legacy pinctrl driver's initcall. This dependency
# must survive DT compilation so the scan waits for the provider.
pinmux_phandle = nodes['/pinmux@70000014'].get('phandle') or nodes['/pinmux@70000014']['linux,phandle']
assert struct.unpack('>4I', nodes['/gpio@6000d000']['gpio-ranges']) == (struct.unpack('>I', pinmux_phandle)[0], 0, 0, 224)

if profile in ('diagnostic', 'panelbus', 'display'):
    config = (artifacts / 'kernel.config').read_text().splitlines()
    for option in ['SMP', 'CACHE_L2X0', 'DEBUG_LL', 'DEBUG_UNCOMPRESS', 'NET',
                   'INPUT', 'MFD_CPCAP', 'REGULATOR_MAX8649', 'BRCMFMAC', 'TEGRA_IOMMU_GART',
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
    if profile != 'display':
        assert 'CONFIG_DRM=y' not in config and 'CONFIG_DRM=m' not in config
        assert nodes['/host1x@50000000']['status'] == b'disabled\0'
    assert nodes['/usb@c5000000']['compatible'] == b'nvidia,tegra20-udc\0'
    assert nodes['/usb-phy@c5000000']['dr_mode'] == b'peripheral\0'
    assert 'motorola,xoom-bigpart' in nodes['/sdhci@c8000600']
    assert '/i2c@7000c000/touchscreen@5b' not in nodes
    if profile != 'display':
        assert '/panel' not in nodes
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
    if profile in ('panelbus', 'display'):
        for option in ['I2C', 'I2C_TEGRA', 'I2C_CHARDEV', 'REGULATOR', 'REGULATOR_FIXED_VOLTAGE']:
            assert f'CONFIG_{option}=y' in config, option
        if profile == 'panelbus':
            assert 'CONFIG_BACKLIGHT_LP855X=y' not in config and 'CONFIG_BACKLIGHT_LP855X=m' not in config
        assert nodes['/i2c@7000c000']['status'] == b'okay\0'
        assert nodes['/aliases']['i2c0'] == b'/i2c@7000c000\0'
        assert [n for n in nodes if n.startswith('/i2c@7000c000/')] == (['/i2c@7000c000/backlight@2c'] if profile == 'display' else [])
        rail = nodes['/panel-power']
        assert struct.unpack('>III', rail['gpio'])[1:] == (10, 0)
        assert 'enable-active-high' in rail and 'regulator-boot-on' in rail and 'regulator-always-on' in rail
        assert struct.unpack('>I',rail['startup-delay-us']) == (200000,)
        assert struct.unpack('>I',rail['regulator-min-microvolt']) == (5000000,)
        assert struct.unpack('>I',rail['regulator-max-microvolt']) == (5000000,)
        mux=nodes['/pinmux@70000014/panelbus-mux/i2c1']
        assert mux['nvidia,pins'].split(b'\0')[:-1] == [b'spdi', b'spdo']
        assert mux['nvidia,function'] == b'i2c1\0'
        assert nodes['/pinmux@70000014']['pinctrl-0'] == nodes['/pinmux@70000014/panelbus-mux']['phandle']
        assert '/backlight-gate' not in nodes and '/spi@7000d400/pmic@0' not in nodes
        assert 'tegra_i2c_probe' in names and 'reg_fixed_voltage_probe' in names
        if profile == 'display':
            for option in ['DRM', 'DRM_TEGRA', 'DRM_TEGRA_FBDEV', 'DRM_PANEL_SIMPLE', 'BACKLIGHT_LP855X', 'DMA_CMA']:
                assert f'CONFIG_{option}=y' in config, option
            assert 'CONFIG_CMA_SIZE_MBYTES=16' in config
            assert 'CONFIG_LOCALVERSION="-wingray-display"' in config
            assert 'CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE=0x584d001d' in config
            assert nodes['/panel']['compatible'] == b'motorola,wingray-auo-panel\0'
            backlight = nodes['/i2c@7000c000/backlight@2c']
            assert backlight['compatible'].split(b'\0')[:2] == [b'motorola,wingray-p3-lp8550', b'ti,lp8550']
            assert backlight['dev-ctrl'] == b'\x03' and backlight['init-brt'] == b'\x80'
            assert backlight['power-supply'] == nodes['/panel']['power-supply'] == rail['phandle']
            assert nodes['/panel']['backlight'] == backlight['phandle']
            host = '/host1x@50000000'
            assert nodes[host]['status'] == b'okay\0'
            dc = nodes[host+'/dc@54200000']
            assert dc['status'] == b'okay\0'
            clock = nodes['/clock@60006000']['phandle']
            c = struct.unpack('>I', clock)[0]
            # TEGRA20_CLK_DISP1=27, PLL_C=114 from the pinned binding.
            assert struct.unpack('>4I',dc['clocks']) == (c,27,c,114)
            assert struct.unpack('>2I',dc['assigned-clocks']) == (c,114)
            assert struct.unpack('>I',dc['assigned-clock-rates']) == (598000000,)
            assert nodes[host+'/dc@54200000/rgb']['status'] == b'okay\0'
            assert nodes[host+'/dc@54200000/rgb']['nvidia,panel'] == nodes['/panel']['phandle']
            for disabled in ['mpe@54040000','vi@54080000','epp@540c0000','isp@54100000','gr2d@54140000','gr3d@54180000','dc@54240000','hdmi@54280000']:
                assert nodes[host+'/'+disabled]['status'] == b'disabled\0', disabled
            groups = [p for n,p in nodes.items() if n.startswith('/pinmux@70000014/panelbus-mux/') and p.get('nvidia,function') == b'displaya\0']
            assert len(groups) == 31
            assert all('nvidia,pull' not in p for p in groups), 'LCD mux groups have no per-signal pull controls'
            data_pulls = nodes['/pinmux@70000014/panelbus-mux/display-data-pulls']
            control_pulls = nodes['/pinmux@70000014/panelbus-mux/display-control-pulls']
            assert data_pulls['nvidia,pins'].split(b'\0')[:-1] == [b'ld17_0',b'ld19_18',b'ld21_20',b'ld23_22']
            assert struct.unpack('>I',data_pulls['nvidia,pull']) == (1,)
            assert control_pulls['nvidia,pins'].split(b'\0')[:-1] == [b'lc',b'ls']
            assert struct.unpack('>I',control_pulls['nvidia,pull']) == (2,)
            assert 'lp855x_probe' in names and 'tegra_dc_probe' in names and 'tegra_dc_rgb_init' in names
            print('Verified display profile: UP/USB/MMC retained, isolated DC0 RGB, 16MiB CMA, P3 backlight and 598MHz parent assignment; GPU/DC1/HDMI/touch/PMIC disabled.')
            sys.exit(0)
        print('Verified panel-bus profile: same UP/USB/MMC gates; PB2 shared supply and I2C1 only; no display/backlight/touch/network or PMIC control.')
        sys.exit(0)
    else:
        print('Verified diagnostic profile: UP, fixed reservations, USB peripheral/serial and BigPart eMMC, no display/network/input probes.')
    sys.exit(0)
if profile in ('early', 'trace'):
    config = (artifacts / 'kernel.config').read_text().splitlines()
    for option in ['SMP', 'CACHE_L2X0', 'DEBUG_LL', 'DEBUG_UNCOMPRESS', 'BLOCK',
                   'MMC', 'USB', 'DRM', 'MFD_CPCAP', 'REGULATOR_MAX8649', 'BRCMFMAC', 'TEGRA_IOMMU_GART']:
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
