# Image 69g: bypass the 4330-only debug chip validator

25 October 2026. Image 69f passed the SDIO chip match and downloaded
firmware:

```text
DHD: dongle ram size is set to 294912(orig 294912) at 0x0
dhdsdio_download_firmware: firmware path=/system/etc/wifi/bcmdhd_sta.bin,
  nvram path=/system/etc/wifi/nvram_net.txt
dhd_bus_init: enable 0x06, ready 0x06
```

Then it stopped in `dhd_preinit_ioctls`:

```text
dhd_preinit_ioctls: CONFIG_BCMXXX and CHIP ID(4329) is mismatched
dhd_bus_start failed to sync with dongle
dhdsdio_probe: dhd_bus_start failed
sdioh_probe: bcmsdh_probe failed
bcmsdh_sdmmc: probe of mmc1:0001:2 failed with error -12
```

The module is compiled for BCM4330, but the hardware is a 4329. The
`CUSTOMER_HW4_DEBUG` validator aborts on that difference because
`SUPPORT_MULTIPLE_CHIPS` was not defined. Image 69g defines it; the
validator logs the difference but continues into `dhd_bus_start`.

Kernel patch: `0130-wingray-bcmdhd-multichip.patch`.

## Image identity

- Path: `artifacts/androidgpu69g-ready/wingray-android44-gpu.img`
- Size: 4,288,512 bytes
- SHA-256: `0d8d6015bf8f67b606cc45d7fb8789d2cf482a2052311a6ebd5e06e687f62dd8`

## Test

```sh
fastboot flash boot artifacts/androidgpu69g-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, try to connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu69g-report1 \
  --storage-mode android44-readonly
```

## Verification criteria

1. `dhd_bus_start` completes and `wlan0` appears.
2. `wpa_supplicant` starts.
3. Actual association and IP configuration.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
