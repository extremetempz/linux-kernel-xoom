# Image 70q: use the AOSP BCM4329 firmware that postmarketOS uses

25 October 2026. The postmarketOS TF101 work uses the AOSP Broadcom WLAN
package and renames its BCM4329 images to the `fw_bcmdhd*` names:

- `fw_bcm4329.bin` -> `fw_bcmdhd.bin`
- `fw_bcm4329_apsta.bin` -> `fw_bcmdhd_apsta.bin`

Reference: <https://gitlab.com/postmarketOS/pmaports/-/merge_requests/1534>

The Xoom ROM's own `fw_bcmdhd.bin` is the **264140-byte ABG/dual-band**
image, which boots but rejects `chanspecs` and optional preinit iovars. The
AOSP 2.4 GHz image is different:

- `fw_bcm4329.bin`: 246791 bytes, SHA-256
  `aebfff9a29c43dbadc83257990fb9a227b8408a79795e6a474f48dbf1b8d5d0b`
- `fw_bcm4329_apsta.bin`: 267027 bytes, SHA-256
  `9c0b422e10dc25976352871b480605e232a64087d0b391540da615c17d23c288`

Image 70q stages those two files in `/bin`, overlays
`/system/vendor/firmware` with them as `fw_bcmdhd.bin` and
`fw_bcmdhd_apsta.bin`, and points the `bcmdhd` module at the overlaid vendor
path. The `xoom-wpa` wrapper still brings `wlan0` up and logs
`wpa_supplicant -dd` to `/run/wpa.log`.

## Image identity

- Path: `artifacts/androidgpu70q-ready/wingray-android44-gpu.img`
- Size: 4,427,776 bytes
- SHA-256: `63879b192717578a27ecbe17fbaafa843159826febcb918369cde504f1659c64`

## Test

```sh
fastboot flash boot artifacts/androidgpu70q-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70q-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `sta_fw=aosp_246791:246791`
2. Firmware version 4.218.248.44, no chanspec/preinit abort
3. `/run/wpa.log` shows `ifconfig_rc=0` and driver init
4. Scan, association and DHCP/IP
5. Display stable

Image 66 remains the recovery image.
