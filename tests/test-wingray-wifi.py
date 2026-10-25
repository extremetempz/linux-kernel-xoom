#!/usr/bin/env python3
"""Static checks for the TF101 5.90.125 Wi-Fi port."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / "sources/kernel-donor"
DTS = (DONOR / "arch/arm/boot/dts/tegra20-motorola-wingray-gpu-test.dts").read_text()
CFG = (DONOR / "arch/arm/configs/wingray_android44_gpu_fbmap_defconfig").read_text()
PREP = (ROOT / "scripts/prepare-android-gpu.py").read_text()
BUILD = (ROOT / "scripts/build-android-gpu.sh").read_text()
DRV = DONOR / "drivers/net/wireless/bcmdhd-tf101"

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
):
    assert needle in CFG, needle

assert '5.90.125.94' in (DRV / 'include/epivers.h').read_text()
assert 'wl_cfg80211_scan_44' in (DRV / 'wl_cfg80211.c').read_text()
assert 'kthread_create' in (DRV / 'include/linuxver.h').read_text()
assert 'module_param_string(firmware_path' in (DRV / 'dhd_linux.c').read_text()
assert 'REGULATORY_CUSTOM_REG' in (DRV / 'wl_cfg80211.c').read_text()
assert 'skb_mac_header(skb)' in (DRV / 'dhd_linux.c').read_text()
assert 'OOB_INTR_ONLY' in (DRV / 'Makefile').read_text()
assert 'gpio_request(165' in (DRV / 'wl_android.c').read_text()
assert 'gpio_request(162' in (DRV / 'wl_android.c').read_text()
assert 'ap_stub.o' in (DRV / 'Makefile').read_text()

assert 'bcmdhd.ko' in PREP
assert 'xoom-wpa' in PREP
assert 'ifconfig wlan0 up' in PREP
assert 'aosp_246791' in PREP
assert 'bin/bcmdhd_apsta.bin' not in PREP
assert '90852a9d824f2cf5463f24e27e6a6ce659cc89661814f4ec2163ca92d7969aa2' in PREP
assert 'postmarketos_4329' in PREP
assert 'aebfff9a29c43dbadc83257990fb9a227b8408a79795e6a474f48dbf1b8d5d0b' in PREP
assert 'firmware_path=/system/vendor/firmware/fw_bcmdhd.bin' in PREP
assert 'wlan.driver.status' in PREP
assert 'xoom-wifi-load' in PREP
assert 'xoomwifi' in PREP
assert 'service wpa_supplicant' in PREP
assert 'service dhcpcd' in PREP
assert 'WPA_LOG' in (ROOT / 'diagnostic/display-report.sh').read_text()

assert 'bcmdhd.ko' in BUILD
assert '--module BCMDHD_TF101' in BUILD
assert 'bcmdhd-tf101/bcmdhd.ko' in BUILD
print('PASS TF101 5.90.125 / AOSP firmware / PMOS NVRAM scope')
