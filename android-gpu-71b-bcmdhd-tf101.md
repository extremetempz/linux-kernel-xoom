# Image 71b: combined TF101 driver, firmware, NVRAM and load timing

25 October 2026. This combines the working pieces from all three driver
attempts.

70z finally created `wlan0` and booted firmware:

```text
Broadcom Dongle Host Driver: register interface [wlan0]
Firmware version ... 4.218.248.44
ifconfig_rc=0
```

But the driver loaded at **63.1s**, while WifiService started supplicant at
**62.9s**:

```text
wpa_supplicant capability warning @ 62.885
dhd_module_init @ 63.100
WifiHW: Supplicant not running, cannot connect
```

Supplicant ran before `wlan0` existed, so WifiHW unloaded the driver six
times.

## 71b changes

- TF101 bcmdhd **5.90.125.94**
- AOSP `fw_bcm4329.bin` (246791)
- postmarketOS `nvram_4329.txt`
- skip the missing `bcmdhd_wlan` platform device
- power WL_REG_ON GPIO 162 directly, OOB GPIO 165
- **load 40 seconds after boot**, so `wlan0` exists around 43s, before
  WifiService at ~62s
- set `wiphy->regulatory_flags |= REGULATORY_CUSTOM_REG` (70z set the wrong
  `flags` field and logged the regulatory warning)

## Image identity

- Path: `artifacts/androidgpu71b-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `c3545f40d113e36dd39cfe34f3be67c44140469a785852b3f169713e40ba8208`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu71b-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu71b-report1 \
  --storage-mode android44-readonly
```

Check:

1. screen stable
2. `wlan0` exists before Wi-Fi is enabled
3. `boot_delay=40` in `/run/xoom-wifi.log`
4. no `Supplicant not running` before driver load
5. scan/association/DHCP

Recovery: 70t or Image 66.
