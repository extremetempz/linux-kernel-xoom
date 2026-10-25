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
    start xoomawake

service xoomawake /bin/xoom-screen-awake
    class late_start
    user root
    oneshot
    disabled
'''

WIFI_SCRIPT=b'''#!/bin/busybox sh
# Load the 4329 bcmdhd module only after /system provides the ROM firmware
# and calibration file.  This keeps the driver out of the early SDIO probe.
LOG=/run/xoom-wifi.log
: > "$LOG"
/bin/busybox sleep 40
echo "boot_delay=40" >> "$LOG"
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
 [ -r /system/vendor/firmware/fw_bcmdhd.bin ] && [ -r /system/etc/wifi/bcm4329.cal ] && break
 /bin/busybox sleep 1
done
# Android's WifiHW was built for paths under /system/etc/wifi.  Provide those
# names in a RAM overlay without modifying the read-only system partition.
/bin/busybox mkdir -p /run/xoom-wifi-orig
[ ! -r /system/etc/wifi/bcm4329.cal ] || /bin/busybox cp /system/etc/wifi/bcm4329.cal /run/xoom-wifi-orig/
[ ! -r /system/etc/wifi/wpa_supplicant.conf ] || /bin/busybox cp /system/etc/wifi/wpa_supplicant.conf /run/xoom-wifi-orig/
/bin/busybox mount -t tmpfs -o mode=0755,size=4m tmpfs /system/etc/wifi >> "$LOG" 2>&1
if [ -r /bin/nvram_4329.txt ]; then
 /bin/busybox cp /bin/nvram_4329.txt /system/etc/wifi/nvram_net.txt
 /bin/busybox cp /bin/nvram_4329.txt /system/etc/wifi/bcm4329.cal
 echo "nvram=postmarketos_4329" >> "$LOG"
elif [ -r /run/xoom-wifi-orig/bcm4329.cal ]; then
 /bin/busybox cp /run/xoom-wifi-orig/bcm4329.cal /system/etc/wifi/bcm4329.cal
 /bin/busybox cp /run/xoom-wifi-orig/bcm4329.cal /system/etc/wifi/nvram_net.txt
 echo "nvram=system_cal" >> "$LOG"
fi
[ ! -r /run/xoom-wifi-orig/wpa_supplicant.conf ] || /bin/busybox cp /run/xoom-wifi-orig/wpa_supplicant.conf /system/etc/wifi/wpa_supplicant.conf
# The ROM vendor firmware is the dual-band 264140 image.  The AOSP 2.4 GHz
# bcm4329 image (246791) is the one postmarketOS uses with bcmdhd, renamed
# to fw_bcmdhd.bin.  Overlay the vendor directory with that image in RAM.
/bin/busybox mkdir -p /run/xoom-vendor-fw
[ ! -r /system/vendor/firmware/fw_bcmdhd.bin ] || /bin/busybox cp /system/vendor/firmware/fw_bcmdhd.bin /run/xoom-vendor-fw/fw_bcmdhd.bin
[ ! -r /system/vendor/firmware/fw_bcmdhd_apsta.bin ] || /bin/busybox cp /system/vendor/firmware/fw_bcmdhd_apsta.bin /run/xoom-vendor-fw/fw_bcmdhd_apsta.bin
/bin/busybox mount -t tmpfs -o mode=0755,size=2m tmpfs /system/vendor/firmware >> "$LOG" 2>&1
if [ -r /bin/bcmdhd_sta.bin ]; then
 /bin/busybox cp /bin/bcmdhd_sta.bin /system/vendor/firmware/fw_bcmdhd.bin
 echo "sta_fw=aosp_246791:$(/bin/busybox wc -c < /bin/bcmdhd_sta.bin)" >> "$LOG"
else
 [ ! -r /run/xoom-vendor-fw/fw_bcmdhd.bin ] || /bin/busybox cp /run/xoom-vendor-fw/fw_bcmdhd.bin /system/vendor/firmware/fw_bcmdhd.bin
 echo "sta_fw=system_fallback" >> "$LOG"
fi
[ ! -r /run/xoom-vendor-fw/fw_bcmdhd_apsta.bin ] || /bin/busybox cp /run/xoom-vendor-fw/fw_bcmdhd_apsta.bin /system/vendor/firmware/fw_bcmdhd_apsta.bin
/bin/busybox ln -sf /system/vendor/firmware/fw_bcmdhd.bin /system/etc/wifi/bcmdhd_sta.bin
[ ! -r /system/vendor/firmware/fw_bcmdhd_apsta.bin ] || /bin/busybox cp /system/vendor/firmware/fw_bcmdhd_apsta.bin /system/etc/wifi/bcmdhd_apsta.bin
/bin/busybox chmod 0644 /system/vendor/firmware/fw_bcmdhd.bin /system/vendor/firmware/fw_bcmdhd_apsta.bin /system/etc/wifi/bcmdhd_sta.bin /system/etc/wifi/bcmdhd_apsta.bin /system/etc/wifi/bcm4329.cal /system/etc/wifi/nvram_net.txt 2>/dev/null
# WifiHW also insmods /system/lib/modules/bcmdhd.ko on a disable/enable cycle.
/bin/busybox mkdir -p /run/xoom-modules
/bin/busybox cp /lib/modules/bcmdhd.ko /run/xoom-modules/bcmdhd.ko
if [ -d /system/lib/modules ]; then
 /bin/busybox mount -t tmpfs -o mode=0755,size=4m tmpfs /system/lib/modules >> "$LOG" 2>&1
 /bin/busybox cp /run/xoom-modules/bcmdhd.ko /system/lib/modules/bcmdhd.ko
 /bin/busybox ln -sf bcmdhd.ko /system/lib/modules/dhd.ko
 /bin/busybox chmod 0644 /system/lib/modules/bcmdhd.ko
fi
/bin/busybox mkdir -p /data/misc/wifi/sockets /data/misc/dhcp
/bin/busybox chown 1010:1010 /data/misc/wifi /data/misc/wifi/sockets
/bin/busybox chmod 0770 /data/misc/wifi /data/misc/wifi/sockets
/bin/busybox chown 1014:1014 /data/misc/dhcp
/bin/busybox chmod 0770 /data/misc/dhcp
# Use the Android 4.4 socket layout; the ROM config may target a stale path.
if [ ! -e /data/misc/wifi/wpa_supplicant.conf ]; then
 echo "ctrl_interface=DIR=/data/misc/wifi/sockets GROUP=wifi" > /data/misc/wifi/wpa_supplicant.conf
 echo "update_config=1" >> /data/misc/wifi/wpa_supplicant.conf
 /bin/busybox chown 1000:1010 /data/misc/wifi/wpa_supplicant.conf
 /bin/busybox chmod 0660 /data/misc/wifi/wpa_supplicant.conf
fi
# Preload while storage is quiet; wlan0 and firmware are up before WifiService.
/bin/busybox insmod /lib/modules/bcmdhd.ko firmware_path=/system/vendor/firmware/fw_bcmdhd.bin nvram_path=/system/etc/wifi/nvram_net.txt >> "$LOG" 2>&1
rc=$?
echo "insmod_rc=$rc" >> "$LOG"
if [ "$rc" -eq 0 ]; then
 /system/bin/setprop wlan.driver.status ok 2>/dev/null || /bin/setprop wlan.driver.status ok 2>/dev/null
fi
'''

WPA_SCRIPT=b'''#!/bin/busybox sh
LOG=/run/wpa.log
: > "$LOG"
echo "wpa wrapper: bringing wlan0 up" >> "$LOG"
/system/bin/ifconfig wlan0 up >> "$LOG" 2>&1 || /bin/busybox ifconfig wlan0 up >> "$LOG" 2>&1
echo "ifconfig_rc=$?" >> "$LOG"
( /bin/busybox sleep 3; /system/bin/logcat -d -v time -s wpa_supplicant:* > /run/wpa-logcat.txt 2>&1 ) &
exec /system/bin/wpa_supplicant -dd -iwlan0 -Dnl80211 -c/data/misc/wifi/wpa_supplicant.conf -O/data/misc/wifi/sockets -g@android:wpa_wlan0 2>> /run/wpa-stderr.log
'''

WIFI_RC=b'''on boot
    mkdir /data/misc/wifi 0770 wifi wifi
    mkdir /data/misc/wifi/sockets 0770 wifi wifi
    mkdir /data/misc/dhcp 0770 dhcp dhcp
    start xoomwifi

service xoomwifi /bin/xoom-wifi-load
    class late_start
    user root
    oneshot
    disabled

service wpa_supplicant /bin/xoom-wpa
    class main
    socket wpa_wlan0 dgram 660 wifi wifi
    disabled
    oneshot

service dhcpcd /system/bin/dhcpcd -aABKL
    class main
    disabled
    oneshot
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
 files['bin/xoom-wifi-load']=WIFI_SCRIPT
 files['bin/xoom-wpa']=WPA_SCRIPT
 wpa_wext=ROOT/'artifacts/hardware-private/system-bin/wpa_supplicant-wext'
 assert wpa_wext.is_file() and digest(wpa_wext.read_bytes())=='4ec6c543782afd630db40f19bf6510408d7c3f175269a49eba27641ce084a2f5'
 files['bin/wpa_supplicant-wext']=wpa_wext.read_bytes()
 aosp_fw=ROOT/'artifacts/hardware-private/wifi/aosp-fw_bcm4329.bin'
 assert aosp_fw.is_file() and digest(aosp_fw.read_bytes())=='aebfff9a29c43dbadc83257990fb9a227b8408a79795e6a474f48dbf1b8d5d0b'
 files['bin/bcmdhd_sta.bin']=aosp_fw.read_bytes()
 result=ramdisk_entries(original,files)
 module=runtime/'modules/bcmdhd.ko'
 assert module.is_file() and module.stat().st_size > 0
 for d in ('lib','lib/modules','lib/firmware','xoom-firmware'):
  result[d]=Entry(d,stat.S_IFDIR|0o755)
 result['lib/modules/bcmdhd.ko']=Entry('lib/modules/bcmdhd.ko',stat.S_IFREG|0o644,module.read_bytes())
 result['init.xoom-awake.rc']=Entry('init.xoom-awake.rc',stat.S_IFREG|0o644,AWAKE_RC)
 result['init.xoom-wifi.rc']=Entry('init.xoom-wifi.rc',stat.S_IFREG|0o644,WIFI_RC)
 result['init.rc']=dataclasses.replace(result['init.rc'],data=result['init.rc'].data+b'\nimport /init.xoom-awake.rc\nimport /init.xoom-wifi.rc\n')
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
