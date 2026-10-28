#!/usr/bin/env python3
"""Pack only a matching built-in accelerated Android runtime; no device operations."""
from pathlib import Path
import argparse,gzip,lzma,hashlib,importlib.util,json,struct
from android44_image import pack_newc,boot_image
from android_gpu import validate_artifacts
from retained_console_profile import selected_retained_dt, ECC_DT
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kernel-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
k=a.kernel_dir.resolve();out=a.output_dir.resolve();assert k.is_relative_to(ROOT/'artifacts') and out.is_relative_to(ROOT/'artifacts') and not out.exists()
spec=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/prepare-android-gpu.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
validate_artifacts(k,require_framebuffer_translation=True)
archive=pack_newc(m.entries(k));assert gzip.decompress((k/'builtin-initramfs.cpio.gz').read_bytes())==archive
assert (k/'runtime-source.cpio').read_bytes()==archive
retained_dt=selected_retained_dt((k/'kernel.config').read_text());retained=retained_dt is not None
wakeirq='CONFIG_MFD_CPCAP_WINGRAY_IRQ_TEST=y\n' in (k/'kernel.config').read_text()
kernel=(k/'zImage').read_bytes();dtname=retained_dt if retained else 'tegra20-motorola-wingray-android44-wakeirq' if wakeirq else 'tegra20-motorola-wingray-android44-displaypm' if 'CONFIG_FB_TEGRA_WINGRAY_DISPLAY_PM=y\n' in (k/'kernel.config').read_text() else 'tegra20-motorola-wingray-android44-battery' if 'CONFIG_BATTERY_WINGRAY_MONITOR=y\n' in (k/'kernel.config').read_text() else 'tegra20-motorola-wingray-android44-bluetooth' if 'CONFIG_RFKILL_WINGRAY_BT=y\n' in (k/'kernel.config').read_text() else 'tegra20-motorola-wingray-android44-gpu-fbmap';dt=(k/(dtname+'.dtb')).read_bytes();combined=(k/'zImage-dtb').read_bytes()
assert struct.unpack_from('<I',kernel,36)[0]==0x016f2818 and combined==kernel+dt
ram=lzma.compress(pack_newc({}),format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32);image=boot_image(combined,ram);assert len(image)<8388608
sha=lambda v:hashlib.sha256(v).hexdigest()
out.mkdir();(out/'wingray-android44-gpu.img').write_bytes(image);(out/'ramdisk.cpio.xz').write_bytes(ram)
dc_test='CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n' in (k/'kernel.config').read_text()
dc_trace='CONFIG_FB_TEGRA_WINGRAY_DC_TRACE_TEST=y\n' in (k/'kernel.config').read_text()
manifest={'purpose':'combined RAM-data Android with original NVIDIA EGL/gralloc/HWC; hardware untested',
 'dc_hang_trace_test':dc_trace,'dc_test_default_armed':False,
 'dc_resume_experimental':dc_test,'dc_resume_hardware_validated':False,
 'retained_console_test':retained,'retained_console_hardware_validated':False,
 'retained_console_ecc_test':retained_dt==ECC_DT,'retained_console_ecc_hardware_validated':False,
 'cpcap_irq_only_test':wakeirq,'power_key_polling':not wakeirq,'hardware_wake_validated':False,
 'display_power_test':wakeirq or dtname.endswith('displaypm'),'soc_suspend_enabled':False,'battery_monitoring_only':wakeirq or dtname.endswith(('battery','displaypm')),'battery_hardware_tested':False,
 'kernel_profile':'android44-wakeirqdc' if dc_trace else 'android44-wakeirqecc' if retained_dt==ECC_DT else 'android44-wakeirqtrace' if retained else 'android44-wakeirq' if wakeirq else 'android44-displaydc' if dc_test else 'android44-displaypm' if dtname.endswith('displaypm') else 'android44-battery' if dtname.endswith('battery') else 'android44-bluetooth' if dtname.endswith('bluetooth') else 'android44-gpu','expected_kernel_release':m.RELEASE,'trace_cookie':'0x584d0060',
 'sha256':sha(image),'size':len(image),'kernel_sha256':sha(combined),'system_map_sha256':sha((k/'System.map').read_bytes()),
 'device_tree':dtname,'builtin_runtime':True,'runtime_archive_sha256':sha(archive),'ramdisk_sha256':sha(ram),
 'bluetooth_experimental':'CONFIG_RFKILL_WINGRAY_BT=y\n' in (k/'kernel.config').read_text(),'bluetooth_hardware_tested':False,'hardware_tested':False,'android_booted':False,'accelerated_android_proven':False,
 'system_mount':'fixed p8 ext4 ro,noload,nosuid,nodev','data_cache':'tmpfs only',
 'preserved_features':['SMP2','PL310','P3 touch wiring','USB serial','full eMMC/BigPart geometry','Motorola AUO/LP8550 wiring and timing'],
 'limits':['Legacy display replaces modern DRM; combined hardware behavior unverified.','Initial framebuffer posting supports synchronous linear packed RGB only.','Wi-Fi follows 73k; Bluetooth is opt-in and hardware unvalidated; no DVFS/suspend/charging-control enablement.'],
 'source_sha256':{str(f.relative_to(ROOT)):sha(f.read_bytes()) for f in [Path(__file__),ROOT/'scripts/prepare-android-gpu.py',ROOT/'scripts/android_gpu.py',ROOT/'scripts/build-android-gpu.sh',ROOT/'scripts/prepare_android_gpu_inputs.py',ROOT/'scripts/bluetooth_profile.py',ROOT/'scripts/battery_profile.py',ROOT/'scripts/display_power_profile.py',ROOT/'scripts/wakeirq_profile.py',ROOT/'scripts/retained_console_profile.py',ROOT/'scripts/build-display-lights.sh',ROOT/'android/lights/lights.c',ROOT/'android/lights/kitkat_lights_abi.h',ROOT/'scripts/android44_image.py',ROOT/'scripts/prepare-android44.py',*[ROOT/'diagnostic'/n for n in ['android44-gpu-bootstrap.sh','android44-gpu-report.sh','bluetooth-setup.sh','bluetooth-report.sh','battery-report.sh','power-report.sh','display-backlight-cycle.sh','fb-blank-test.sh','android44-init.sh','android-service-runner.sh','server.sh','pstore-report.sh','usb-report-loop.sh','report.sh']]]}}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Prepared combined Android/NVIDIA image, NOT flashed:',len(image),'bytes SHA256',manifest['sha256'])
