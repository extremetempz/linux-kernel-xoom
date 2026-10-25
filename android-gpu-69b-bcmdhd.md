> **Superseded by Image 69d.** 69d adds the WifiHW `/system` path overlays
> and `wlan.driver.status=ok`, which are required for Android to skip its
> stale insmod path. Use `android-gpu-69d-bcmdhd.md`.

# Image 69b: bcmdhd 4329 connectivity candidate

25 October 2026. Image 69 switched from brcmfmac to the 4.4 donor bcmdhd
driver, built as `dhd.ko` with the BCM4329 SDIO alias and the Xoom firmware/
calibration paths.  This revision adds a clean Android 4.4 supplicant socket
configuration and Wi-Fi state diagnostics.

## Image identity

- Path: `artifacts/androidgpu69b-ready/wingray-android44-gpu.img`
- Size: 4,288,512 bytes
- SHA-256: `18ac6bcbb4d5147e35548ee25949287b4ba179c61cfaed12d30cc22e3906e08d`

## Wi-Fi path

- `dhd.ko` is stripped to about 1.0 MiB and packed at `/lib/modules/dhd.ko`.
- `xoomwifi` runs at `post-fs-data`, after `/system` is mounted:
  - waits for `fw_bcmdhd.bin` and `bcm4329.cal`;
  - creates `/data/misc/wifi` and `/data/misc/dhcp`;
  - writes a clean `wpa_supplicant.conf`;
  - loads `dhd.ko` with the system firmware and calibration paths.
- Android `wpa_supplicant` and `dhcpcd` services are defined.
- `XOOM_WIFI_STATE` in the report captures `/run/xoom-wifi.log`, the dhd
  module parameters, `/proc/net/wireless`, `iwconfig` if present and
  `dumpsys wifi`.
- `xoomawake` screen-awake and volume-down wake remain.

## Test

```sh
fastboot flash boot artifacts/androidgpu69b-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, try to connect to a network, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu69b-report1 \
  --storage-mode android44-readonly
```

## Verification criteria

The objective is not complete until the report shows:

1. `insmod_rc=0` and `DHD_MODULE present`;
2. `wlan0` in `XOOM_NET`;
3. `wpa_supplicant` running/started;
4. an actual association and IP configuration.

If `insmod_rc` is nonzero, inspect the log for vermagic/dependency errors. If
the module loads but no `wlan0` appears, the next issue is firmware/calibration
or 4329-vs-4330 chip configuration. If `wlan0` appears but WifiHW fails, the
remaining integration point is Android's module-path expectation.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
