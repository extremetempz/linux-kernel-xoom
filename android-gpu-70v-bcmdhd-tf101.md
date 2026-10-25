# Image 70v: TF101 5.90.125 driver with AOSP firmware and PMOS NVRAM

25 October 2026. This replaces the 2.6-era bcmdhd 5.90.195 host driver with
the ASUS TF101 3.1 kernel driver, **bcmdhd 5.90.125.94** — the host-driver
generation paired with the 4.218.248.44 BCM4329 firmware and used by the
postmarketOS TF101 WiFi fix.

## What changed

- Imported `drivers/net/wireless/bcmdhd` from the TF101 3.1 kernel at
  `5ddd9654ec52599fbef71657ad2e03b3cdacee31`.
- Built it against Linux 4.4 with:
  - `kthread_create` instead of `kernel_thread`
  - `skb_mac_header()`
  - `ndo_set_rx_mode`
  - 4.4 cfg80211 wrappers for `add_virtual_intf`, `del_virtual_intf`,
    `scan` and TX-power callbacks
  - `REGULATORY_CUSTOM_REG`
- Kept the Xoom board wiring:
  - WL_REG_ON/reset GPIO 162
  - OOB host-wake GPIO 165, `IRQF_TRIGGER_HIGH`
  - AOSP `fw_bcm4329.bin` (246791) as `fw_bcmdhd.bin`
  - postmarketOS `nvram_4329.txt` as NVRAM
  - `bcmdhd.ko`, `/run/xoom-wifi.log`, `xoom-wpa`, DHCP service

## Static validation

- module version string: `5.90.125.94`
- SDIO alias: `sdio:c*v02D0d4329*`
- no `kernel_thread`, `daemonize`, `strnicmp` or `ap_eth_ctl` unresolved
  symbols
- cfg80211 scan/interface callbacks compiled with 4.4 wrappers
- firmware, NVRAM, GPIO and module paths are present in the initramfs

This is the exact host-driver/firmware/NVRAM generation that works on the
Tegra 2 + BCM4329 TF101. Hardware validation is still required on the Xoom.

## Image identity

- Path: `artifacts/androidgpu70v-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `66c814808d541fd7711e585ce656212da46ec8c4c79d52e78170cdf2a60f337d`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70v-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70v-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `insmod_rc=0`, module version 5.90.125.94 in dmesg
2. `sta_fw=aosp_246791:246791`, `nvram=postmarketos_4329`
3. `Firmware version ... 4.218.248.44`
4. `wlan0` up; `/run/wpa.log` driver init; scan results
5. Association and DHCP/IP
6. Display stable

Image 66 remains the recovery image.
