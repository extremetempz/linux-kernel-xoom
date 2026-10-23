#!/usr/bin/env python3
"""Check actual compiled resource DT/config, preserved controls and rejections."""
import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT/'sources/kernel-donor'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load('resource_gate', ROOT/'scripts/legacy_resources.py')
dt = load('touch_dt', ROOT/'tests/test-wingray-touch-dt.py')


def reject(call):
    try:
        call()
    except (AssertionError, ValueError, IndexError, struct.error):
        return
    raise AssertionError('Invalid resource profile accepted')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dtc', required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--kconfig-build', type=Path,
                        help='Idle build directory from build-wingray.sh; config restored afterward')
    args = parser.parse_args()
    # Compare old board sources/config to the prior hardware-tested lineage,
    # rather than comparing a candidate to a simultaneously edited control.
    paths = subprocess.check_output([
        'git', '-C', str(TREE), 'ls-tree', '-r', '--name-only', 'b6483deb',
        'arch/arm/boot/dts',
    ], text=True).splitlines()
    paths = [p for p in paths if Path(p).name.startswith('tegra20-motorola-wingray')]
    paths += ['arch/arm/boot/dts/tegra20.dtsi',
              'arch/arm/configs/wingray_android44_smp2_defconfig']
    for path in paths:
        original = subprocess.check_output(['git', '-C', str(TREE), 'show', 'b6483deb:'+path])
        assert (TREE/path).read_bytes() == original, 'Tested source modified: '+path

    control = dt.compile_dt('tegra20-motorola-wingray-android44-smp2', args.dtc)
    nodes = dt.compile_dt(gate.NAME, args.dtc)
    gate.validate_nodes(nodes, control)
    gate.validate_artifacts(args.artifacts)
    assert gate.parse_dtb((args.artifacts/(gate.NAME+'.dtb')).read_bytes()) == nodes

    mutations = [
        (gate.HEAP, 'reg', struct.pack('>II', 0x2f000000, 0x10000000)),
        (gate.HEAP, 'usage-mask', struct.pack('>I', 0x20000000)),
        (gate.HEAP, 'buddy-size', struct.pack('>I', 3)),
        (gate.HEAP, 'memory-region', struct.pack('>I', 0)),
        (gate.VIDEO, 'reg', struct.pack('>II', 0x30000000, 0x10000000)),
        ('/host1x@50000000', 'status', b'okay\0'),
        ('/host1x@50000000/dc@54200000', 'status', b'okay\0'),
        ('/iommu@7000f024', 'status', b'okay\0'),
        ('/panel', 'status', b'okay\0'),
        ('/', 'compatible', b'samsung,p4wifi\0nvidia,tegra20\0'),
        ('/pinmux@70000014', 'unexpected-property', b'changed'),
        ('/gpio@6000d000', 'gpio-ranges', b'changed'),
    ]
    for path, key, value in mutations:
        bad = deepcopy(nodes)
        bad[path][key] = value
        reject(lambda: gate.validate_nodes(bad, control))
    for path in ['/nvmap/carveouts/iram', '/iovmm-gart']:
        bad = deepcopy(nodes)
        bad[path] = {'status': b'okay\0'}
        reject(lambda: gate.validate_nodes(bad, control))
    bad = deepcopy(nodes)
    del bad[gate.VIDEO]['no-map']
    reject(lambda: gate.validate_nodes(bad, control))

    text = (args.artifacts/'kernel.config').read_text()

    def changed(name, value):
        lines = [s for s in text.splitlines()
                 if not s.startswith('CONFIG_'+name+'=') and
                 not s.startswith('# CONFIG_'+name+' is not set')]
        return '\n'.join(lines + ['CONFIG_'+name+'='+value])+'\n'

    for name in gate.REQUIRED:
        reject(lambda n=name: gate.validate_config(changed(n, 'n')))
    for name in gate.FORBIDDEN:
        for value in ['y', 'm']:
            reject(lambda n=name, v=value: gate.validate_config(changed(n, v)))
    reject(lambda: gate.validate_config(text.replace('maxcpus=2', 'maxcpus=1')))

    if args.kconfig_build:
        build = args.kconfig_build.resolve()
        config = build/'out/.config'
        original = config.read_bytes()
        make = ['make', '-C', str(build/'source'), 'O='+str(build/'out'),
                'ARCH=arm', 'CROSS_COMPILE='+str(build/'toolchain/bin/arm-linux-androideabi-'),
                'olddefconfig']
        try:
            for conflict in ['TEGRA_GRHOST', 'TEGRA_RPC', 'TEGRA_IOVMM_GART', 'CPU_FREQ']:
                config.write_bytes(original)
                subprocess.run([str(build/'source/scripts/config'), '--file', str(config),
                                '-e', conflict, '-e', 'TEGRA_NVMAP_WINGRAY_RESOURCES'], check=True)
                subprocess.run(make, check=True, stdout=subprocess.DEVNULL)
                lines = config.read_text().splitlines()
                assert 'CONFIG_'+conflict+'=y' in lines, conflict
                assert 'CONFIG_TEGRA_NVMAP_WINGRAY_RESOURCES=y' not in lines, conflict
        finally:
            config.write_bytes(original)
            subprocess.run(make, check=True, stdout=subprocess.DEVNULL)
            assert config.read_bytes() == original

    with tempfile.TemporaryDirectory(prefix='xoom-resource-artifacts-') as temp:
        temp = Path(temp)
        for name in ['zImage', 'zImage-dtb', gate.NAME+'.dtb', 'control-smp2.dtb',
                     'kernel.config', 'System.map']:
            shutil.copyfile(args.artifacts/name, temp/name)
        image = (temp/'zImage-dtb').read_bytes()
        (temp/'zImage-dtb').write_bytes(image[:-1])
        reject(lambda: gate.validate_artifacts(temp))
        (temp/'zImage-dtb').write_bytes(image)
        symbols = (temp/'System.map').read_text()
        (temp/'System.map').write_text(symbols+'\nc0100000 t tegra_dvfs_probe\n')
        reject(lambda: gate.validate_artifacts(temp))
    print('PASS compiled Motorola-only carveout profile, pinned board sources, engine/GART/IRAM/power/config negative controls. Offline only.')


if __name__ == '__main__':
    main()
