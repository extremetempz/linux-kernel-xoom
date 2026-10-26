#!/usr/bin/env python3
"""Static checks for the Image 67 CPCAP power-key foundation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT / "sources/kernel-donor"
DTS = (DONOR / "arch/arm/boot/dts/tegra20-motorola-wingray-gpu-test.dts").read_text()
MFD = (DONOR / "drivers/mfd/motorola-cpcap.c").read_text()
HDR = (DONOR / "include/linux/mfd/motorola-cpcap.h").read_text()
CFG = (DONOR / "arch/arm/configs/wingray_android44_gpu_fbmap_defconfig").read_text()

for needle in (
    'spi@7000d600',
    'status = "okay"',
    'pinctrl-0 = <&wingray_cpcap_spi>',
    'compatible = "motorola,cpcap"',
    'interrupt-parent = <&intc>',
    'interrupts = <GIC_SPI 86 IRQ_TYPE_LEVEL_HIGH>',
):
    assert needle in DTS, needle

for pin in ("spia", "spib", "spic", "spig"):
    assert f'nvidia,pins = "{pin}"' in DTS
    assert 'nvidia,function = "spi2"' in DTS

for needle in (
    "cpcap_register_pwrkey",
    "KEY_POWER",
    "CPCAP_BIT_ON_S",
    "cpcap_pwrkey_work",
    "schedule_delayed_work(&cpcap->pwrkey_work",
    "CPCAP INTS%d=%04x",
    "CPCAP INT%d=%04x",
    "CPCAP ON interrupt unmasked",
    "CPCAP power key polling registered",
    'of_machine_is_compatible("motorola,wingray")',
    "rev != 0",
):
    assert needle in MFD, needle

assert "CPCAP_BIT_ON_S" in HDR
assert "CPCAP_BIT_ON_I" in HDR
for needle in (
    "CONFIG_SPI=y",
    "CONFIG_SPI_TEGRA20_SLINK=y",
    "CONFIG_DMADEVICES=y",
    "CONFIG_TEGRA20_APB_DMA=y",
    "CONFIG_MFD_CPCAP=y",
):
    assert needle in CFG, needle
assert "CONFIG_REGULATOR_CPCAP=y" not in CFG
print("PASS CPCAP power-key transport/config/DT scope")
