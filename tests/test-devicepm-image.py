#!/usr/bin/env python3
"""Validate built image90 scope, linked RAM helper and preserved image89."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pm_preparation_profile import blocked_pm
from android_gpu import validate_artifacts
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--image',type=Path,required=True);a=p.parse_args()
cfg=(a.runtime/'kernel.config').read_text();assert blocked_pm(cfg)
for key in ('MOTOROLA_WINGRAY_DEVICEPM_TEST','MOTOROLA_WINGRAY_FREEZER_TEST','MFD_CPCAP'):
 assert f'CONFIG_{key}=y\n' in cfg,key
 if key!='MOTOROLA_WINGRAY_DEVICEPM_TEST':
  bad=cfg.replace(f'CONFIG_{key}=y\n',f'# CONFIG_{key} is not set\n')
  try: blocked_pm(bad)
  except AssertionError: pass
  else: raise AssertionError('Missing dependency accepted: '+key)
validate_artifacts(a.runtime,require_framebuffer_translation=True)
archive=gzip.decompress((a.runtime/'builtin-initramfs.cpio.gz').read_bytes())
assert archive==(a.runtime/'runtime-source.cpio').read_bytes()
for helper in ('devicepm-cycle','freezer-cycle','wake-arm-cycle'):
 assert helper.encode() in archive
 assert (ROOT/'diagnostic'/(helper+'.sh')).read_bytes() in archive
m=json.loads((a.image/'manifest.json').read_text())
assert m['kernel_profile']=='android44-devicepmtest' and m['selected_device_pm_test']
assert m['sleep_entry_blocked'] and not m['soc_suspend_enabled'] and not m['cpu_sleep_tested']
assert not m['device_suspend_tested'] and not m['hardware_wake_validated']
image=(a.image/'wingray-android44-gpu.img').read_bytes();assert hashlib.sha256(image).hexdigest()==m['sha256']
assert len(image)==m['size']<8388608
old=ROOT/'artifacts/freezer89-reviewed-ready/wingray-android44-gpu.img'
assert hashlib.sha256(old.read_bytes()).hexdigest()=='edfe9c59d3f1852506efec5c89429b727ad0c8a03f4dfc1d86dff86b0d6f1015'
dt='tegra20-motorola-wingray-android44-wakeirqecc.dtb'
assert (a.runtime/dt).read_bytes()==(ROOT/'artifacts/freezer89-runtime'/dt).read_bytes()
# Source archives must not arrange an automatic DEVICEPMTEST at boot.
for path in ('diagnostic/android44-init.sh','diagnostic/android44-gpu-bootstrap.sh'):
 assert b'DEVICEPMTEST' not in (ROOT/path).read_bytes()
print('PASS image90 artifact validation, linked fixed helpers, no automatic test, image89 preserved; hardware untested')
