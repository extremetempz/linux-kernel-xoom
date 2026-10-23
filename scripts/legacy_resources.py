"""Offline checks for the isolated Motorola nvmap resource profile.

DT token decoding follows the existing Wingray verifier/test implementation.
This checks build artifacts, not live memory ownership or hardware behavior.
"""
from pathlib import Path
import struct

NAME = 'tegra20-motorola-wingray-legacy-resources'
VIDEO = '/reserved-memory/legacy-video@2e800000'
HEAP = '/nvmap/carveouts/generic@30000000'
DISABLED_NODES = {
    '/host1x@50000000', '/host1x@50000000/dc@54200000', '/panel',
    '/memory-controller@7000f000', '/iommu@7000f024',
    '/memory-controller@7000f400',
}
REQUIRED = {
    'MACH_MOTOROLA_WINGRAY', 'ARCH_TEGRA_2x_SOC', 'SMP', 'CACHE_L2X0',
    'HAVE_ARCH_PFN_VALID', 'TEGRA_DOWNSTREAM', 'TEGRA_NVMAP',
    'TEGRA_NVMAP_WINGRAY_RESOURCES', 'ARM_APPENDED_DTB', 'ARM_ATAG_DTB_COMPAT',
    'DEVTMPFS', 'DEVTMPFS_MOUNT', 'USB_CHIPIDEA_UDC', 'USB_TEGRA_PHY',
    'USB_G_SERIAL', 'MMC_SDHCI_TEGRA', 'MOTOROLA_XOOM_BIGPART',
    'REGULATOR_FIXED_VOLTAGE', 'I2C_TEGRA', 'TOUCHSCREEN_ATMEL_MXT',
}
FORBIDDEN = {
    'MACH_SAMSUNG_VARIATION_TEGRA', 'MACH_SAMSUNG_P4WIFI', 'CPU_FREQ',
    'CPU_IDLE', 'SUSPEND', 'HOTPLUG_CPU', 'MOTOROLA_XOOM_BOOT_TRACE',
    'MOTOROLA_XOOM_SMP_TRACE', 'DRM', 'TEGRA_HOST1X', 'TEGRA20_MC',
    'TEGRA_GRHOST', 'TEGRA_DC', 'TEGRA_OVERLAY', 'TEGRA_DC_EXTENSIONS',
    'FB_TEGRA', 'FB_TEGRA_CMC623', 'FB_TEGRA_WINGRAY_LEGACY',
    'TEGRA_IOVMM', 'TEGRA_IOVMM_GART', 'TEGRA_IOMMU_GART', 'IOMMU_API',
    'TEGRA_RPC', 'TEGRA_AVP', 'TEGRA_AVP_KERNEL_ON_MMU', 'TEGRA_MEDIASERVER',
    'NVMAP_ALLOW_SYSMEM', 'NVMAP_RECLAIM_UNPINNED_VM', 'NVMAP_HIGHMEM_ONLY',
    'NVMAP_CONVERT_CARVEOUT_TO_IOVMM', 'NVMAP_CARVEOUT_KILLER',
    'NVMAP_CARVEOUT_COMPACTOR', 'NVMAP_PAGE_POOLS', 'NVMAP_VPR',
    'NVMAP_CACHE_MAINT_BY_SET_WAYS',
}


def cells(value):
    assert len(value) % 4 == 0
    return struct.unpack('>' + 'I' * (len(value) // 4), value)


def parse_dtb(data):
    assert 40 <= len(data) <= 1024 * 1024, 'DTB size outside bound'
    magic, total, cursor, strings = struct.unpack_from('>4I', data)
    assert magic == 0xd00dfeed and total == len(data), 'Bad DTB header'
    assert 40 <= cursor < strings < total
    nodes, stack = {}, []
    for _ in range(32768):
        assert cursor + 4 <= strings
        token, = struct.unpack_from('>I', data, cursor)
        cursor += 4
        if token == 1:
            end = data.index(0, cursor, strings)
            stack.append(data[cursor:end].decode('ascii'))
            assert len(stack) <= 64
            cursor = (end + 4) & ~3
            path = '/'.join(stack) or '/'
            assert path not in nodes, 'Duplicate DT node'
            nodes[path] = {}
        elif token == 2:
            assert stack
            stack.pop()
        elif token == 3:
            assert stack and cursor + 8 <= strings
            length, offset = struct.unpack_from('>II', data, cursor)
            cursor += 8
            assert cursor + length <= strings and strings + offset < total
            at = strings + offset
            name = data[at:data.index(0, at)].decode('ascii')
            props = nodes['/'.join(stack) or '/']
            assert name not in props, 'Duplicate DT property'
            props[name] = data[cursor:cursor+length]
            cursor = (cursor + length + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            assert not stack
            return nodes
        else:
            raise AssertionError('Bad DT token')
    raise AssertionError('DT token count outside bound')


def validate_nodes(nodes, control):
    additions = {'/nvmap', '/nvmap/carveouts', HEAP}
    assert set(nodes) - set(control) == additions, 'Unexpected resource additions'
    assert not set(control) - set(nodes), 'Existing board node removed'
    # This profile adds its new reference after the existing references.
    # Ignore only provider identity fields; all existing reference cells must
    # remain byte-identical too (do not normalize away a changed GPIO target).
    for path in control:
        old = {k: v for k, v in control[path].items()
               if k not in ('phandle', 'linux,phandle')}
        new = {k: v for k, v in nodes[path].items()
               if k not in ('phandle', 'linux,phandle')}
        if path == '/':
            old.pop('model')
            assert new.pop('model') == b'Motorola Xoom P3 legacy resource experiment (carveout only)\0'
        if path in DISABLED_NODES:
            assert new.pop('status') == b'disabled\0', path
            old.pop('status', None)
        assert new == old, 'Changed tested board properties: ' + path
    assert nodes['/']['compatible'] == b'motorola,wingray\0nvidia,tegra20\0'
    assert cells(nodes['/memory']['reg']) == (0, 0x40000000)
    reserve = nodes[VIDEO]
    assert cells(reserve['reg']) == (0x2e800000, 0x11800000)
    assert 'no-map' in reserve and 'reusable' not in reserve
    phandle = cells(reserve.get('phandle', reserve.get('linux,phandle', b'')))
    assert len(phandle) == 1 and phandle[0]
    assert nodes['/nvmap'] == {
        'compatible': b'nvidia,tegra-nvmap\0', 'status': b'okay\0',
        '#address-cells': struct.pack('>I', 1),
        '#size-cells': struct.pack('>I', 1), 'ranges': b'',
    }
    assert nodes['/nvmap/carveouts'] == {
        '#address-cells': struct.pack('>I', 1),
        '#size-cells': struct.pack('>I', 1), 'ranges': b'',
    }
    assert nodes[HEAP] == {
        'reg': struct.pack('>II', 0x30000000, 0x10000000),
        'reg-names': b'generic-0\0', 'buddy-size': struct.pack('>I', 0x8000),
        'usage-mask': struct.pack('>I', 1), 'memory-region': struct.pack('>I', phandle[0]),
    }, 'Heap differs from the isolated Motorola generic carveout'
    # No IRAM resource or GART node is added; framebuffer ranges remain out
    # of the only allocatable heap: fb0 8 MiB + fb1 16 MiB precede 0x30000000.
    assert 0x2e800000 + 0x800000 + 0x1000000 == 0x30000000


def validate_config(text):
    config = {}
    for line in text.splitlines():
        if line.startswith('CONFIG_'):
            key, value = line[7:].split('=', 1)
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            key, value = line[9:-11], 'n'
        else:
            continue
        assert key not in config, 'Duplicate config option: ' + key
        config[key] = value
    for key in REQUIRED:
        assert config.get(key) == 'y', key
    for key in FORBIDDEN:
        assert config.get(key, 'n') == 'n', key
    assert config['LOCALVERSION'] == '"-wingray-legacy-resources"'
    assert config['BUILD_ARM_APPENDED_DTB_IMAGE_NAMES'] == '"'+NAME+'"'
    assert config['NR_CPUS'] == '2'
    cmd = config['CMDLINE']
    assert cmd.count('maxcpus=') == 1 and 'maxcpus=2' in cmd
    assert 'clk_ignore_unused' in cmd and 'regulator_ignore_unused' in cmd


def validate_artifacts(directory):
    directory = Path(directory)
    image = (directory/'zImage').read_bytes()
    dtb = (directory/(NAME+'.dtb')).read_bytes()
    assert len(image) >= 48 and struct.unpack_from('<I', image, 36)[0] == 0x016f2818
    assert (directory/'zImage-dtb').read_bytes() == image + dtb
    validate_nodes(parse_dtb(dtb), parse_dtb((directory/'control-smp2.dtb').read_bytes()))
    validate_config((directory/'kernel.config').read_text())
    symbols = {s.split()[-1] for s in (directory/'System.map').read_text().splitlines()
               if len(s.split()) == 3}
    assert 'nvmap_probe' in symbols
    for name in ['nvhost_probe', 'tegra_dc_probe', 'tegra_drm_probe',
                 'tegra_fb_register', 'gart_probe', 'tegra_gart_probe',
                 'tegra_dvfs_probe']:
        assert not any(s == name or s.startswith(name+'.') for s in symbols), name
