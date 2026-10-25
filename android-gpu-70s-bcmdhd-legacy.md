# Image 70s: postmarketOS/AOSP firmware plus BCM4329 NVRAM

25 October 2026. The postmarketOS TF101 fix has **two** parts:

1. AOSP BCM4329 firmware renamed to `fw_bcmdhd*`
2. A dedicated `nvram_4329.txt` with the BCM4329 board description

Reference: <https://gitlab.postmarketos.org/postmarketOS/pmaports/-/merge_requests/1534>
and
<https://gitlab.postmarketos.org/postmarketOS/pmaports/-/raw/e40ecc2fc2b10a30d1cf95f681a01c9ca4877ef6/device/testing/device-asus-tf101/nvram_4329.txt>

Image 70q only took the firmware; the NVRAM was still the Xoom’s
`bcm4329.cal`. Image 70s overlays the PMOS NVRAM text (adapted MAC to the
Xoom’s `00:90:4c:12:34:56`) as both:

- `/system/etc/wifi/nvram_net.txt`
- `/system/etc/wifi/bcm4329.cal`

It contains the chip identity, board type, board flags, PA calibration,
RSSI parameters and `ccode=ALL`, which the old calibration file does not.
The driver loads it with:

```text
nvram_path=/system/etc/wifi/nvram_net.txt
```

The AOSP 2.4 GHz firmware and `bcmdhd` module name remain.

## Image identity

- Path: `artifacts/androidgpu70s-ready/wingray-android44-gpu.img`
- Size: 4,429,824 bytes
- SHA-256: `722b7302e57e756ba60b55bc4dc29f6dfdc326d05dc0493dab612e20d33adb6a`

## Test

```sh
fastboot flash boot artifacts/androidgpu70s-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70s-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `sta_fw=aosp_246791:246791`, `nvram=postmarketos_4329`
2. Firmware up without `get chanspecs`/preinit abort
3. `wlan0` stays up; `/run/wpa.log` shows driver init
4. Scan results, association, DHCP/IP
5. Display stable

Image 66 remains the recovery image.
