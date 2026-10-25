#!/usr/bin/env python3
"""Static checks for the Image 68 BCM4329 Wi-Fi foundation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / "sources/kernel-donor"
DTS = (DONOR / "arch/arm/boot/dts/tegra20-motorola-wingray-gpu-test.dts").read_text()
CFG = (DONOR / "arch/arm/configs/wingray_android44_gpu_fbmap_defconfig").read_text()
PREP = (ROOT / "scripts/prepare-android-gpu.py").read_text()
BUILD = (ROOT / "scripts/build-android-gpu.sh").read_text()
MAKE = (DONOR / "drivers/net/wireless/bcmdhd/Makefile").read_text()

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
    'CONFIG_LEGACY_BCMDHD=m',
):
    assert needle in CFG, needle

assert 'CONFIG_NETDEVICES is not set' not in CFG
assert 'CONFIG_MODULES=y' in CFG
assert 'CONFIG_CFG80211=y' in CFG
assert 'CONFIG_LEGACY_BCMDHD=m' in CFG
assert 'dhd.ko' in PREP
assert 'bcmdhd-legacy' in (ROOT / 'sources/kernel-donor/drivers/net/wireless/bcmdhd-legacy/Makefile').read_text()
assert 'wlan.driver.status' in PREP
assert '/system/lib/modules' in PREP
assert 'bcmdhd_sta.bin' in PREP
assert 'xoom-wifi-load' in PREP
assert 'xoomwifi' in PREP
assert 'service wpa_supplicant' in PREP
assert 'service dhcpcd' in PREP
assert 'dhd.ko' in BUILD
assert '--module LEGACY_BCMDHD' in BUILD
assert '\nEXTRA_CFLAGS += -DCONFIG_DTS\n' not in MAKE
print('PASS BCM4329 Wi-Fi SDIO/config/firmware scope')
