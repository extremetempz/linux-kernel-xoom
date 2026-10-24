"""Offline gates for the fixed-clock, offscreen Wingray rendering experiment."""
from pathlib import Path
import struct
from host_test import validate_tree as host_tree, validate_config as host_config
from legacy_resources import parse_dtb, cells

NAME = 'tegra20-motorola-wingray-gpu-test'
HOST = '/host1x@50000000'

def startup_cookie(directory):
    import re
    text = (Path(directory)/'kernel.config').read_text()
    match = re.search(r'^CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE=(0x[0-9a-f]+)$',text,re.M)
    assert match and int(match[1],16) in (0x584d0049,0x584d0050)
    return int(match[1],16)

def validate_artifacts(directory, *, startup_trace=False, trace_cookie=0x584d0049):
    p = Path(directory)
    host = parse_dtb((p/'control-host.dtb').read_bytes())
    host_tree(host, parse_dtb((p/'control-resources.dtb').read_bytes()),
              parse_dtb((p/'control-smp2.dtb').read_bytes()))
    dtb = (p/(NAME+'.dtb')).read_bytes()
    nodes = parse_dtb(dtb)
    expected = {n: dict(v) for n, v in host.items()}
    expected['/']['model'] = b'Motorola Xoom P3 fixed-clock offscreen GPU diagnostic\0'
    car = cells(host[HOST]['clocks'])[0]
    expected[HOST+'/gr2d@54140000'].update({
        'clocks': struct.pack('>4I', car, 21, car, 19),
        'clock-names': b'gr2d\0epp\0', 'status': b'okay\0'})
    expected[HOST+'/gr3d@54180000'].update({
        'clock-names': b'gr3d\0', 'status': b'okay\0'})
    assert nodes == expected, 'Unexpected board/resource changes'
    text = (p/'kernel.config').read_text()
    if startup_trace:
        assert trace_cookie in (0x584d0049,0x584d0050)
        for line in ('CONFIG_MOTOROLA_XOOM_GPU_STARTUP_TRACE=y',
                     'CONFIG_MOTOROLA_XOOM_SMP_TRACE=y',
                     f'CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE={trace_cookie:#x}',
                     'CONFIG_LOCALVERSION="-wingray-gpu-trace"'):
            assert text.count(line+'\n') == 1, line
        text = text.replace('CONFIG_MOTOROLA_XOOM_SMP_TRACE=y\n',
                            '# CONFIG_MOTOROLA_XOOM_SMP_TRACE is not set\n')
        text = text.replace('-wingray-gpu-trace', '-wingray-gpu-test')
    else:
        assert 'CONFIG_MOTOROLA_XOOM_GPU_STARTUP_TRACE=y' not in text
    # Reuse every host-profile requirement after accounting for the four
    # deliberately changed switches and the diagnostic identity.
    replacements = {
        'CONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST=y': '# CONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST is not set',
        '# CONFIG_TEGRA_GRHOST_WINGRAY_HOST_TEST is not set': 'CONFIG_TEGRA_GRHOST_WINGRAY_HOST_TEST=y',
        'CONFIG_TEGRA_GRHOST_WINGRAY_LEGACY_SUBMIT=y': '# CONFIG_TEGRA_GRHOST_WINGRAY_LEGACY_SUBMIT is not set',
        'CONFIG_TEGRA_SEMA_STANDALONE=y': '# CONFIG_TEGRA_SEMA_STANDALONE is not set',
    }
    control = text
    for before, after in replacements.items():
        assert text.count(before+'\n') == 1, before
        control = control.replace(before+'\n', after+'\n')
    host_config(control.replace('-wingray-gpu-test', '-wingray-host-test'))
    kernel = (p/'zImage').read_bytes()
    assert struct.unpack_from('<I', kernel, 36)[0] == 0x016f2818
    assert (p/'zImage-dtb').read_bytes() == kernel+dtb
    symbols = {line.split()[-1] for line in (p/'System.map').read_text().splitlines() if len(line.split()) == 3}
    for name in ('nvmap_probe', 'nvhost_probe', 'nvhost_gr3d_prepare_power_off',
                 'nvhost_module_prepare_client', 'trpc_sema_init'):
        assert any(n == name or n.startswith(name+'.') for n in symbols), name
    for name in ('tegra_dc_probe', 'tegra_drm_probe', 'tegra_fb_register',
                 'tegra_gart_probe', 'tegra_dvfs_probe', 'wingray_host_test_init'):
        assert not any(n == name or n.startswith(name+'.') for n in symbols), name
