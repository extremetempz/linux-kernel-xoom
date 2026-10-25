> **Superseded by Image 70l.** 70j used a private firmware that did not boot
> and kept the module named dhd.  Use `android-gpu-70l-bcmdhd-legacy.md`.

# Image 70j: firmware from /bin, the path that is actually present

25 October 2026. Image 70i still logged:

```text
sta_fw=system_fallback
dhd_bus_start: dhdsdio_probe_download failed.
firmware = /xoom-firmware/bcmdhd_sta.bin
```

Neither `/lib/firmware` nor the new root `/xoom-firmware` was visible to the
runtime loader, although `/bin/xoom-wifi-load` and `/lib/modules/dhd.ko`
were. Image 70j places the private firmware beside the loader itself:

- `/bin/bcmdhd_sta.bin` (222,310 bytes, 5.90.100.410)
- `/system/etc/wifi/bcmdhd_sta.bin` symlinks to it
- `dhd.ko` loads with `firmware_path=/bin/bcmdhd_sta.bin`
- `/run/xoom-wifi.log` records `sta_fw=private_bin:222310`

This guarantees the same filesystem that supplies the Wi-Fi loader also
supplies the firmware.

## Image identity

- Path: `artifacts/androidgpu70j-ready/wingray-android44-gpu.img`
- Size: 4,511,744 bytes
- SHA-256: `cde46f5b2cdb02e84daed367bb6f376e37ee49e1a1940175333fea86be475f42`

## Test

```sh
fastboot flash boot artifacts/androidgpu70j-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70j-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `sta_fw=private_bin:222310`
2. Firmware version `5.90.100.410`
3. No firmware download failure or `get chanspecs` error
4. `wlan0` UP, scan results, supplicant
5. Association and DHCP/IP
6. Display stable

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
