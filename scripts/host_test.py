"""Offline gates for the isolated Wingray host-clock/IRQ diagnostic."""
from pathlib import Path
import struct
from legacy_resources import parse_dtb, cells, validate_nodes, REQUIRED, FORBIDDEN

NAME = 'tegra20-motorola-wingray-host-test'
HOST = '/host1x@50000000'

def validate_tree(nodes, resource, smp):
    validate_nodes(resource, smp)
    assert set(nodes) == set(resource), 'Added or removed board nodes'
    expected = {p: dict(v) for p, v in resource.items()}
    expected['/']['model'] = b'Motorola Xoom P3 host-only diagnostic\0'
    expected[HOST].update({'compatible': b'nvidia,tegra20-host1x\0nvhost-bus\0',
                           'status': b'okay\0', 'clock-names': b'host1x\0'})
    assert nodes == expected, 'Host diagnostic changed additional board wiring/resources'
    assert cells(nodes[HOST]['reg']) == (0x50000000, 0x24000)
    assert cells(nodes[HOST]['interrupts']) == (0, 65, 4, 0, 67, 4)
    assert cells(nodes[HOST]['clocks'])[1:] == (28,)
    assert cells(nodes[HOST]['resets'])[1:] == (28,)
    assert nodes[HOST]['reset-names'] == b'host1x\0'
    for path, props in nodes.items():
        if path.startswith(HOST+'/') and '/' not in path[len(HOST)+1:]:
            assert props.get('status') == b'disabled\0', 'Enabled host child: '+path

def validate_config(text):
    config = {}
    for line in text.splitlines():
        if line.startswith('CONFIG_'):
            key, value = line[7:].split('=', 1)
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            key, value = line[9:-11], 'n'
        else:
            continue
        assert key not in config
        config[key] = value
    required = (REQUIRED - {'TEGRA_NVMAP_WINGRAY_RESOURCES'}) | {
        'TEGRA_GRHOST', 'TEGRA_GRHOST_WINGRAY_HOST_TEST', 'TEGRA_GRHOST_USE_NVMAP'}
    forbidden = (FORBIDDEN - {'TEGRA_GRHOST'}) | {'TEGRA_NVMAP_WINGRAY_RESOURCES'}
    for key in required: assert config.get(key) == 'y', key
    for key in forbidden: assert config.get(key, 'n') == 'n', key
    assert config['LOCALVERSION'] == '"-wingray-host-test"'
    assert config['BUILD_ARM_APPENDED_DTB_IMAGE_NAMES'] == '"'+NAME+'"'
    assert config['NR_CPUS'] == '2'
    assert config['CMDLINE'].count('maxcpus=') == 1 and 'maxcpus=2' in config['CMDLINE']
    assert 'clk_ignore_unused' in config['CMDLINE'] and 'regulator_ignore_unused' in config['CMDLINE']

def validate_artifacts(directory):
    p = Path(directory)
    kernel = (p/'zImage').read_bytes(); dtb = (p/(NAME+'.dtb')).read_bytes()
    assert struct.unpack_from('<I', kernel, 36)[0] == 0x016f2818
    assert (p/'zImage-dtb').read_bytes() == kernel+dtb
    validate_tree(parse_dtb(dtb), parse_dtb((p/'control-resources.dtb').read_bytes()),
                  parse_dtb((p/'control-smp2.dtb').read_bytes()))
    validate_config((p/'kernel.config').read_text())
    names={line.split()[-1] for line in (p/'System.map').read_text().splitlines() if len(line.split())==3}
    for name in ['nvmap_probe','nvhost_probe','nvhost_module_busy_checked','wingray_host_test_init']:
        assert name in names, name
    for name in ['tegra_dc_probe','tegra_drm_probe','tegra_fb_register','tegra_gart_probe','tegra_dvfs_probe']:
        assert not any(n==name or n.startswith(name+'.') for n in names), name
