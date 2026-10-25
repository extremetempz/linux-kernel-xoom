> **Superseded by Image 68c.** The 68b report enumerated the SDIO card and
> recognized BCM4329, but the empty NVRAM file failed with -22. Image 68c
> supplies a minimal NVRAM entry. Use `android-gpu-68c-wifi-nvram.md`.

# Image 68b: 3.3V SDIO card rail for BCM4329

25 October 2026. Image 68 reached the BCM4329 SDIO card, but enumeration
failed:

```text
sdhci-tegra c8000200.sdhci: no support for card's volts
mmc1: error -22 whilst initialising SDIO card
```

The BCM4329 card is powered from the 3.3V WLAN rail; the 1.8V fixed
regulator is the IO rail. Image 68 used the 1.8V rail as `vmmc`, so the host
OCR did not intersect the card OCR.

## Fix

- Keep `wlan_power` (GPIO U4, 1.8V) as `vqmmc`.
- Add an always-on 3.3V fixed `wlan_vmmc` and use it as `vmmc`.
- The firmware staging, brcmfmac/SDIO configuration and report sections are
  unchanged from Image 68.

Kernel patch: `0123-wingray-bcm4329-vmmc.patch`

## Image identity

- Path: `artifacts/androidgpu68b-ready/wingray-android44-gpu.img`
- Size: 4,024,320 bytes
- SHA-256: `e80c050cc8f043362fff60fcfdf69b9d0bc55ceab223e632c637002715ac5df6`

## Hardware test

```sh
fastboot flash boot artifacts/androidgpu68b-ready/wingray-android44-gpu.img
fastboot reboot
```

Then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu68b-report1 \
  --storage-mode android44-readonly
```

Look for:

- `mmc1: new SDIO card` or equivalent enumeration instead of `-22`;
- `brcmfmac` firmware load messages;
- `wlan0` in `/sys/class/net`;
- the `XOOM_NET` section.

## Expected next failure

The staged `bcmdhd_sta.bin` is Android bcmdhd firmware. If `brcmfmac`
rejects it, the report will identify the firmware failure. The next step
would then be either a matching brcmfmac 4329 image or the original
bcmdhd/bcm4329 driver.

Android `wpa_supplicant`/DHCP/settings integration is still not included.
Image 66 remains the recovery image.
