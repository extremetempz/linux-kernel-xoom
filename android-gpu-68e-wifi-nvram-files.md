# Image 68e: alternate BCM4329 firmware and on-device NVRAM discovery

25 October 2026. Image 68d reached the chip with the matching brcmfmac
firmware and no longer logged `HT Avail timeout`, but it never created
`wlan0`. The only Wi-Fi-related state was the SDIO card and chip detection.

Image 68e changes three things:

1. Uses the alternate `bcm4329-fullmac-4.bin` firmware
   (SHA-256 `ee87d73b...82ee`) under the brcmfmac filename.
2. Fixes the init service name to the alphanumeric `xoomawake`; Android init
   rejected both hyphen and underscore names in the earlier images.
3. Adds a report section listing `/system/etc/wifi`,
   `/system/vendor/firmware`, `/system/etc/firmware`, and the contents of any
   `nvram_net.txt`/`nvram.txt` there.

The last point is important: the minimal `macaddr` NVRAM may not contain the
Xoom board parameters the firmware needs. The report will show whether the
original ROM has a real NVRAM file.

## Image identity

- Path: `artifacts/androidgpu68e-ready/wingray-android44-gpu.img`
- Size: 4,059,136 bytes
- SHA-256: `6add6f225424fc4a6a49531f037bb24283f20dd151a6627d0e6c5f2ad87f9ed7`

## Hardware test

```sh
fastboot flash boot artifacts/androidgpu68e-ready/wingray-android44-gpu.img
fastboot reboot
```

Capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu68e-report1 \
  --storage-mode android44-readonly
```

Look for:

- `XOOM_WIFI_FILES` showing a real `nvram_net.txt`;
- `wlan0` in `XOOM_NET`;
- any brcmfmac firmware/clock error.

## Interpretation

- `wlan0` present → kernel Wi-Fi works; next is Android supplicant/DHCP.
- No `wlan0` but a real NVRAM file on `/system` → stage that NVRAM next.
- No `wlan0` and no NVRAM file → the minimal NVRAM/board parameters or the
  brcmfmac driver/firmware pair remains the blocker.

Android `wpa_supplicant`/DHCP/settings are still not integrated. Power key
remains parked; volume-down is the working wake key. Image 66 remains the
recovery image.
