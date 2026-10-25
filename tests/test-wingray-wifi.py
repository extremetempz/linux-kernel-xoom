#!/usr/bin/env python3
"""Static checks for the Image 68 BCM4329 Wi-Fi foundation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / "sources/kernel-donor"
DTS = (DONOR / "arch/arm/boot/dts/tegra20-motorola-wingray-gpu-test.dts").read_text()
CFG = (DONOR / "arch/arm/configs/wingray_android44_gpu_fbmap_defconfig").read_text()
PREP = (ROOT / "scripts/prepare-android-gpu.py").read_text()
BUILD = (ROOT / "scripts/build-android-gpu.sh").read_text()

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
    'CONFIG_BRCMFMAC=y',
    'CONFIG_BRCMFMAC_SDIO=y',
):
    assert needle in CFG, needle

assert 'CONFIG_NETDEVICES is not set' not in CFG
assert 'brcmfmac4329-sdio.bin' in PREP
assert 'macaddr=02:00:00:00:00:01' in PREP
assert 'service xoomawake' in PREP
assert 'ee87d73bc8b54aa29e343490297ca1294f71a1a4f66c845e6b301770c94082ee' in PREP
assert '--enable NETDEVICES --enable WLAN --enable BRCMFMAC --enable BRCMFMAC_SDIO' in BUILD
print('PASS BCM4329 Wi-Fi SDIO/config/firmware scope')
