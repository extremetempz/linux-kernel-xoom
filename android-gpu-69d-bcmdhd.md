> **Superseded by Image 69e.** 69d loaded the module but never registered
> the SDIO function because bcmdhd was built with CONFIG_DTS and no
> `android,bcmdhd_wlan` node existed. Use `android-gpu-69e-bcmdhd.md`.

# Image 69d: WifiHW-compatible bcmdhd 4329 module

25 October 2026. Android's `libhardware_legacy/wifi/wifi.c` requires both
`wlan.driver.status=ok` and a matching entry in `/proc/modules` before it
will skip its own `insmod`.  It also reads firmware/calibration from
`/system/etc/wifi` and may load `/system/lib/modules/dhd.ko` on a
disable/enable cycle.

Image 69d provides those paths in RAM without modifying the read-only system
partition.

## Changes

- `xoomwifi` overlays `/system/etc/wifi` with:
  - `bcmdhd_sta.bin` (from `fw_bcmdhd.bin`)
  - `bcmdhd_apsta.bin`
  - `nvram_net.txt` (from `bcm4329.cal`)
  - `bcm4329.cal`
- It also overlays `/system/lib/modules` with `dhd.ko`, so WifiHW's module
  path exists.
- After a successful `insmod`, it sets `wlan.driver.status=ok`.
- Loads the module with:
  - `firmware_path=/system/etc/wifi/bcmdhd_sta.bin`
  - `nvram_path=/system/etc/wifi/nvram_net.txt`
- Keeps `wpa_supplicant`/`dhcpcd` services, clean supplicant config,
  `xoomawake` and volume-down wake.
- Adds `XOOM_WIFI_STATE` diagnostics.

## Image identity

- Path: `artifacts/androidgpu69d-ready/wingray-android44-gpu.img`
- Size: 4,288,512 bytes
- SHA-256: `836ba12e08382c28d0e1b6bc0f9b15b8076e8d6221237f8258bc739f7858a70a`

## Test

```sh
fastboot flash boot artifacts/androidgpu69d-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, try to connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu69d-report1 \
  --storage-mode android44-readonly
```

## Verification criteria

1. `insmod_rc=0`, `DHD_MODULE present`, `wlan.driver.status` is observable
   through the loaded module and `wlan0` exists.
2. `wlan0` appears in `XOOM_NET`.
3. `wpa_supplicant` starts.
4. An actual association and IP configuration.

If `insmod_rc` is nonzero, the log gives the module failure. If the module
loads but no `wlan0`, the next suspect is 4329-vs-4330 chip handling or the
firmware/calibration pair. If `wlan0` appears but WifiHW still fails, capture
the `XOOM_WIFI_STATE` section.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
