#!/usr/bin/env python3
"""Validate new CPU controls against pinned, physically tested configuration/DT.

No device operations. DTC compiles the actual trees; negative artifact cases
exercise the production kernel verifier, including SMP tracer/clock safety.
"""
import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / 'sources/kernel-donor'
spec = importlib.util.spec_from_file_location('touch_dt', ROOT/'tests/test-wingray-touch-dt.py')
dt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dt)


def config(text):
    values = {}
    for line in text.splitlines():
        if line.startswith('CONFIG_'):
            key, value = line.split('=', 1)
            values[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dtc', required=True)
    p.add_argument('--artifacts', type=Path)
    p.add_argument('--profile', choices=['android44-l2', 'android44-smp'])
    a = p.parse_args()
    base_path = 'arch/arm/configs/wingray_android44_touch_defconfig'
    pinned = subprocess.check_output(['git','-C',str(TREE),'show','fd24d166:'+base_path], text=True)
    assert (TREE/base_path).read_text() == pinned, 'Hardware-tested touch config changed'
    base = config(pinned)
    allowed = {'CONFIG_LOCALVERSION','CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES',
               'CONFIG_CACHE_L2X0','CONFIG_MOTOROLA_XOOM_BOOT_TRACE_COOKIE'}
    for suffix in ['l2', 'smp']:
        path = TREE/f'arch/arm/configs/wingray_android44_{suffix}_defconfig'
        c = config(path.read_text())
        allowed_here = set(allowed)
        if suffix == 'smp':
            allowed_here |= {'CONFIG_SMP','CONFIG_SMP_ON_UP','CONFIG_NR_CPUS','CONFIG_HOTPLUG_CPU',
                             'CONFIG_CMDLINE', *[k for k in base if k.startswith('CONFIG_MOTOROLA_XOOM_BOOT_TRACE')]}
        changed = {k for k in base.keys()|c.keys() if base.get(k) != c.get(k)}
        assert changed <= allowed_here, changed - allowed_here
        assert c['CONFIG_CACHE_L2X0'] == 'y'
        assert c['CONFIG_CPU_FREQ'] == c['CONFIG_CPU_IDLE'] == c['CONFIG_SUSPEND'] == 'n'
        if suffix == 'smp':
            assert c['CONFIG_SMP']=='y' and c['CONFIG_NR_CPUS']=='2'
            assert c['CONFIG_HOTPLUG_CPU']=='n' and 'maxcpus=1' in c['CONFIG_CMDLINE']
            assert c['CONFIG_MOTOROLA_XOOM_BOOT_TRACE']=='n'
        else:
            assert c['CONFIG_SMP']=='n' and c['CONFIG_MOTOROLA_XOOM_BOOT_TRACE']=='y'
        original = dt.compile_dt('tegra20-motorola-wingray-android44-touch', a.dtc)
        candidate = dt.compile_dt('tegra20-motorola-wingray-android44-'+suffix, a.dtc)
        original['/'].pop('model'); candidate['/'].pop('model')
        assert candidate == original, 'CPU profile changed board wiring/resources'
    if a.artifacts:
        assert a.profile
        subprocess.run(['python3',str(ROOT/'scripts/verify-kernel.py'),str(a.artifacts),a.profile],check=True)
        with tempfile.TemporaryDirectory(prefix='xoom-cpu-verifier-') as t:
            out = Path(t)
            for f in a.artifacts.iterdir():
                if f.is_file(): shutil.copyfile(f, out/f.name)
            text = (out/'kernel.config').read_text()
            mutations = [text.replace('# CONFIG_CPU_FREQ is not set','CONFIG_CPU_FREQ=y'),
                         text.replace('CONFIG_CACHE_L2X0=y','# CONFIG_CACHE_L2X0 is not set')]
            if a.profile == 'android44-smp':
                mutations += [text + '\nCONFIG_MOTOROLA_XOOM_BOOT_TRACE=y\n',
                              text.replace('maxcpus=1','maxcpus=2'),text.replace('CONFIG_NR_CPUS=2','CONFIG_NR_CPUS=4')]
            for bad in mutations:
                assert bad != text
                (out/'kernel.config').write_text(bad)
                result = subprocess.run(['python3',str(ROOT/'scripts/verify-kernel.py'),str(out),a.profile],capture_output=True)
                assert result.returncode != 0, 'Unsafe CPU profile accepted'
    print('PASS: tested touch control unchanged; CPU DT/resources isolated; fixed clocks and SMP tracer gates enforced.')


if __name__ == '__main__': main()
