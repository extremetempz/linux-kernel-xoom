> **Superseded by Image 70j.** 70i still reported `sta_fw=system_fallback`;
> only `/bin` content is reliably visible to the loader. Use
> `android-gpu-70j-bcmdhd-legacy.md`.

# Image 70i: load firmware from a path that is actually visible

25 October 2026. Image 70h still logged:

```text
sta_fw=system_fallback
dhd_bus_start: dhdsdio_probe_download failed.
firmware = /lib/firmware/bcmdhd_sta.bin
```

The initramfs archive contains `/lib/firmware/bcmdhd_sta.bin` (222,310
bytes), but the runtime `/lib` path is shadowed/not visible to the Wi-Fi
loader, while `/lib/modules/dhd.ko` happens to work through the module
overlay. The direct `/lib/firmware` firmware path therefore failed.

Image 70i stages the same 5.90.100.410 firmware at
`/xoom-firmware/bcmdhd_sta.bin`, alongside `/bin`, which is definitely
visible. It:

- logs `sta_fw=private_root:222310` when the private image is selected;
- symlinks `/system/etc/wifi/bcmdhd_sta.bin` to the root firmware;
- loads `dhd.ko` with `firmware_path=/xoom-firmware/bcmdhd_sta.bin`;
- keeps WL_REG_ON GPIO U2, OOB IRQ, fwpath aliases and the 4.4 cfg80211
  fixes.

## Image identity

- Path: `artifacts/androidgpu70i-ready/wingray-android44-gpu.img`
- Size: 4,366,336 bytes
- SHA-256: `ab2ce60946c958076be44148474c0bb063be932f7e872a31c26d2270254b8459`

## Test

```sh
fastboot flash boot artifacts/androidgpu70i-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70i-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `/run/xoom-wifi.log` says `sta_fw=private_root:222310`.
2. Firmware version 5.90.100.410.
3. No firmware download failure or `get chanspecs` error.
4. `wpa_supplicant` brings `wlan0` up, scan results appear.
5. Association and DHCP/IP.
6. Display remains stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
