#!/usr/bin/env python3
"""Prepare a separate RAM-only NVIDIA Android runtime; never flashes or mounts."""
from pathlib import Path
import argparse,dataclasses,gzip,hashlib,json,re,stat,subprocess,sys
from android44_image import Entry,original_entries,ramdisk_entries,pack_newc,boot_image,digest,BUSYBOX_SHA256
from prepare_android_gpu_inputs import graphics_hashes
# Reuse the already checked static-runtime/ROM-reference gates.
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('android_pack',ROOT/'scripts/prepare-android44.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
RELEASE='4.4.147-wingray-android44-gpu'

# The kernel has no suspend or power-key wake source yet.  Android's 120 s
# screen timeout therefore leaves the panel dark with no way to wake it.
# Keep this development runtime awake after boot so the UI remains usable;
# remove this workaround once a PMIC/GPIO power-key wake path exists.
AWAKE_SCRIPT=b'''#!/bin/busybox sh
# Keep the display awake while the kernel exposes no power-key wake source.
LOG=/run/xoom-screen-awake.log
: > "$LOG"
echo "screen-awake service started" >> "$LOG"
for attempt in 1 2 3 4 5 6 7 8 9 10; do
 echo "=== attempt $attempt ===" >> "$LOG"
 /bin/busybox timeout -s KILL 5 /system/bin/settings put system screen_off_timeout 2147483647 >> "$LOG" 2>&1
 echo "screen_off_timeout_rc=$?" >> "$LOG"
 /bin/busybox timeout -s KILL 5 /system/bin/settings put global stay_on_while_plugged_in 7 >> "$LOG" 2>&1
 echo "stay_on_rc=$?" >> "$LOG"
 /bin/busybox timeout -s KILL 5 /system/bin/svc power stayon true >> "$LOG" 2>&1
 echo "svc_stayon_rc=$?" >> "$LOG"
 timeout_value=$(/bin/busybox timeout -s KILL 5 /system/bin/settings get system screen_off_timeout 2>/dev/null)
 stay_value=$(/bin/busybox timeout -s KILL 5 /system/bin/settings get global stay_on_while_plugged_in 2>/dev/null)
 echo "readback=$timeout_value/$stay_value" >> "$LOG"
 [ "$timeout_value" = "2147483647" ] && [ "$stay_value" = "7" ] && exit 0
 /bin/busybox sleep 2
done
echo "FAILED: display may still time out" >> "$LOG"
exit 1
'''

AWAKE_RC=b'''# Development-only display wake workaround.  The kernel has no suspend or
# power-key wake source, so keep the panel on after Android boots.
on property:sys.boot_completed=1
    start xoom_screen_awake

service xoom_screen_awake /bin/xoom-screen-awake
    class late_start
    user root
    oneshot
    disabled
'''

def entries(runtime):
 config=(runtime/'kernel.config').read_bytes()
 for line in (b'CONFIG_LOCALVERSION="-wingray-android44-gpu"\n',b'CONFIG_ANDROID_BINDER_IPC_32BIT=y\n',b'CONFIG_FB_TEGRA_WINGRAY_LEGACY=y\n',b'CONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST=y\n'):
  assert line in config,line
 original=original_entries((ROOT/'artifacts/hardware-private/backup-boot.img').read_bytes())
 busybox=base.check_static_arm(ROOT/'artifacts/busybox-static-armv5l','v5T');assert digest(busybox)==BUSYBOX_SHA256
 hashes,refs=base.system_hashes();gpu=graphics_hashes()
 hashes+=b''.join((sha+'  '+name+'\n').encode() for name,sha in sorted(gpu.items()))
 files={'bin/busybox':busybox,'bin/android44-system-sha256':hashes}
 for name,source in [('android44-abi-probe','android44-abi-probe.c'),('touch-events','touch-events.c'),('cpu-handoff-probe','cpu-handoff-probe.c')]:
  files['bin/'+name]=base.checked_runtime(runtime,name,ROOT/'diagnostic'/source,RELEASE,config)
 assert json.loads((runtime/'display-pattern-manifest.json').read_text())['legacy_wingray_layout']
 files['bin/display-pattern']=base.checked_runtime(runtime,'display-pattern',ROOT/'diagnostic/display-pattern.c')
 helpers={'init':'android44-init.sh','bin/android44-bootstrap':'android44-gpu-bootstrap.sh',
  'bin/android-service-runner':'android-service-runner.sh','bin/usb-report-loop':'usb-report-loop.sh',
  'bin/diagnostic-server':'server.sh','bin/diagnostic-report':'report.sh','bin/android44-report':'android44-gpu-report.sh',
  'bin/display-report':'display-report.sh','bin/touch-report':'touch-report.sh','bin/soc-report':'soc-report.sh'}
 for name,source in helpers.items():
  path=ROOT/'diagnostic'/source;subprocess.run(['bash','-n',str(path)],check=True);files[name]=path.read_bytes()
 files['bin/xoom-screen-awake']=AWAKE_SCRIPT
 result=ramdisk_entries(original,files)
 # BCM4329 fullmac firmware for the SDIO Wi-Fi bring-up.  brcmfmac and
 # bcmdhd use different file names for the same chip firmware; stage the
 # known Xoom bcmdhd image under the brcmfmac name and an empty NVRAM file.
 firmware=ROOT/'artifacts/hardware-private/wifi/bcmdhd_sta.bin'
 assert firmware.is_file() and digest(firmware.read_bytes())=='462e89e7bcf1f4fd701933d9cb80e795acca27a7c80300e42661d7e3bc6f5ea7'
 for d in ('lib','lib/firmware','lib/firmware/brcm'):
  result[d]=Entry(d,stat.S_IFDIR|0o755)
 result['lib/firmware/brcm/brcmfmac4329-sdio.bin']=Entry('lib/firmware/brcm/brcmfmac4329-sdio.bin',stat.S_IFREG|0o644,firmware.read_bytes())
 result['lib/firmware/brcm/brcmfmac4329-sdio.txt']=Entry('lib/firmware/brcm/brcmfmac4329-sdio.txt',stat.S_IFREG|0o644,b'')
 result['init.xoom-awake.rc']=Entry('init.xoom-awake.rc',stat.S_IFREG|0o644,AWAKE_RC)
 result['init.rc']=dataclasses.replace(result['init.rc'],data=result['init.rc'].data+b'\nimport /init.xoom-awake.rc\n')
 # Match the working original ROM's permissions only for the three GPU channels used.
 u=result['ueventd.stingray.rc'];perms=b'\n# Original Wingray NVIDIA channels; explicit paths, no block access.\n'+b''.join((name+' 0666 root root\n').encode() for name in ('/dev/nvhost-ctrl','/dev/nvhost-gr2d','/dev/nvhost-gr3d'))
 result[u.name]=dataclasses.replace(u,data=u.data+perms)
 # Keep the old experiment's board identity and RAM-data services; select vendor modules via tegra.
 assert b'ro.hardware=stingray\n' in result['default.prop'].data
 assert b'/system/lib/egl/libGLES_android.so /run/xoom-egl/' not in files['bin/android44-bootstrap']
 assert b'0 1 tegra' in files['bin/android44-bootstrap']
 assert not any(x in files['bin/android44-bootstrap'] for x in (b' gralloc.default ',b'libGLES_android.so /run/xoom-egl'))
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-dir',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
 assert not a.archive.exists();data=pack_newc(entries(a.runtime_dir));a.archive.write_bytes(data)
 print('Prepared combined RAM-only Android/NVIDIA archive:',len(data),'bytes; not a flashable image')
if __name__=='__main__':main()
