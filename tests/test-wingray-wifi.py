#!/usr/bin/env python3
"""Static checks for the native 4.4 bcmdhd Wi-Fi route used by Image 73."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / "sources/kernel-donor"
DTS = (DONOR / "arch/arm/boot/dts/tegra20-motorola-wingray-gpu-test.dts").read_text()
CFG = (DONOR / "arch/arm/configs/wingray_android44_gpu_fbmap_defconfig").read_text()
PREP = (ROOT / "scripts/prepare-android-gpu.py").read_text()
BUILD = (ROOT / "scripts/build-android-gpu.sh").read_text()
DRV = DONOR / "drivers/net/wireless/bcmdhd"

for needle in (
    'sdhci@c8000200',
    'compatible = "brcm,bcm4329-fmac"',
    'wlan-power',
    'wlan-vmmc',
    'regulator-min-microvolt = <3300000>',
    'mmc-pwrseq-simple',
    'interrupts = <TEGRA_GPIO(U, 5) IRQ_TYPE_LEVEL_HIGH>',
):
    assert needle in DTS, needle

for needle in (
    'CONFIG_NETDEVICES=y',
    'CONFIG_WLAN=y',
    'CONFIG_CFG80211=y',
    'CONFIG_BROADCOM_WIFI=y',
    'CONFIG_BCMDHD_FW_PATH="/system/vendor/firmware/fw_bcmdhd.bin"',
    'CONFIG_BCMDHD_NVRAM_PATH="/system/etc/wifi/bcm4329.cal"',
):
    assert needle in CFG, needle
assert 'CONFIG_BCMDHD_TF101' not in CFG
assert 'CONFIG_LEGACY_BCMDHD=m' not in CFG

MAKEFILE = (DRV / 'Makefile').read_text()
assert 'bcmdhd-y := $(DHDOFILES)' in MAKEFILE
assert 'obj-$(DRIVER_TYPE)   += bcmdhd.o' in MAKEFILE
assert (DRV / 'wl_cfg80211.c').is_file()
assert (DRV / 'dhd_linux.c').is_file()
assert 'module_param_string(firmware_path' in (DRV / 'dhd_linux.c').read_text()

CONNECT = (DRV / 'wl_cfg80211.c').read_text()
assert 'wl_bss_connect_done(cfg, ndev, e, data, true)' in CONNECT
assert 'event == WLC_E_ASSOC' in CONNECT
assert 'WL_CHANSPEC_BW_20' in CONNECT
assert 'goto set_ssid' in CONNECT
assert 'wldev_set_band(dev, WLC_BAND_2G)' in CONNECT
assert 'WLC_SET_SSID' in CONNECT
assert 'wldev_iovar_setbuf_bsscfg(dev, "join"' not in CONNECT
assert 'wl_cfg80211_ulb_get_min_bw_chspec(cfg, dev->ieee80211_ptr, bssidx)' not in CONNECT

assert 'bcmdhd.ko' in PREP
assert 'xoom-wpa' in PREP
assert 'ifconfig wlan0 up' in PREP
assert 'aosp_246791' in PREP
assert 'bin/bcmdhd_apsta.bin' not in PREP
assert '90852a9d824f2cf5463f24e27e6a6ce659cc89661814f4ec2163ca92d7969aa2' not in PREP
assert 'postmarketos_4329' not in PREP
assert 'nvram=system_cal' in PREP
assert 'aebfff9a29c43dbadc83257990fb9a227b8408a79795e6a474f48dbf1b8d5d0b' in PREP
assert 'firmware_path=/system/vendor/firmware/fw_bcmdhd.bin' in PREP
assert '/system/bin/wpa_supplicant -dd -iwlan0 -Dnl80211' in PREP
assert 'wpa_supplicant-wext' not in PREP
assert 'wpa-logcat.txt' in PREP
assert 'wlan.driver.status' in PREP
assert 'xoom-wifi-load' in PREP
assert 'xoomwifi' in PREP
assert 'service wpa_supplicant' in PREP
assert 'service dhcpcd' in PREP
assert 'service dhcpcd_wlan0' in PREP
assert 'WPA_LOG' in (ROOT / 'diagnostic/display-report.sh').read_text()

assert 'bcmdhd.ko' in BUILD
assert '--enable BROADCOM_WIFI' in BUILD
assert '--disable LEGACY_BCMDHD' in BUILD
assert '--disable BCMDHD_TF101' in BUILD
assert 'drivers/net/wireless/bcmdhd/bcmdhd.ko' in BUILD
assert 'bcmdhd-tf101/bcmdhd.ko' not in BUILD

runtime = ROOT / 'artifacts/androidgpu73g-runtime/modules/bcmdhd.ko'
if runtime.is_file():
    assert runtime.stat().st_size > 1_000_000
    data = runtime.read_bytes()
    assert b'wl_bss_connect_done' in data
    assert b'bcmdhd' in data

SERIES = ROOT / 'kernel/patches'
assert (SERIES / '0137-wingray-bcmdhd-native-defconfig.patch').is_file()
assert (SERIES / '0138-wingray-bcmdhd-native-module.patch').is_file()
assert (SERIES / '0139-wingray-bcmdhd-native-connect.patch').is_file()
assert not list(SERIES.glob('*tf101*'))
assert not list(SERIES.glob('*bcmdhd-legacy*'))
connect_patch = (SERIES / '0139-wingray-bcmdhd-native-connect.patch').read_text()
assert 'WLC_SET_SSID' in connect_patch
assert 'WL_CHANSPEC_BW_20' in connect_patch
assert 'wl_bss_connect_done(cfg, ndev, e, data, true)' in connect_patch

print('PASS native 4.4 bcmdhd / ASSOC result / 20 MHz WLC_SET_SSID / OEM NVRAM / series')
