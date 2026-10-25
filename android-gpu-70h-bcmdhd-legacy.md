# Image 70h: force the matching firmware into the driver

25 October 2026. Image 70g was built with the private 5.90.100.410 firmware,
but the 70g boot log still reported:

```text
/system/etc/wifi/bcmdhd_sta.bin  264140
Firmware version = wl0: ... version 4.218.248.44
get chanspecs failed with -23
```

The overlay copy had fallen back to `/system/vendor/firmware/fw_bcmdhd.bin`.
Image 70h removes that ambiguity:

- loads `dhd.ko` with
  `firmware_path=/lib/firmware/bcmdhd_sta.bin` directly;
- makes `/system/etc/wifi/bcmdhd_sta.bin` a symlink to the initramfs
  `/lib/firmware/bcmdhd_sta.bin`, so WifiHW/SoftapController cannot replace
  it with the old ROM firmware;
- logs `sta_fw=private:<size>` or `sta_fw=system_fallback` in
  `/run/xoom-wifi.log`;
- keeps the WL_REG_ON GPIO U2 and OOB IRQ fixes.

The staged firmware is 222,310 bytes, version 5.90.100.410, SHA-256
`462e89e7bcf1f4fd701933d9cb80e795acca27a7c80300e42661d7e3bc6f5ea7`.

## Image identity

- Path: `artifacts/androidgpu70h-ready/wingray-android44-gpu.img`
- Size: 4,220,928 bytes
- SHA-256: `521ddbd743143e1b65fb3f374154d7869b0241200ff05dccf467f4ccea1e7baf`

## Test

```sh
fastboot flash boot artifacts/androidgpu70h-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70h-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `/run/xoom-wifi.log` says `sta_fw=private:222310`.
2. Firmware version is 5.90.100.410.
3. No `get chanspecs failed`; `wpa_supplicant` brings `wlan0` up.
4. Scan, association and DHCP/IP.
5. Display remains stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
