# Image 68: BCM4329 Wi-Fi kernel foundation

25 October 2026. The CPCAP power-key investigation is parked. All four CPCAP
INT/INTS banks remained unchanged after the GIC parent fix and nine physical
presses, so the back power button cannot be recovered through the CPCAP path
currently exposed. Volume-down remains the working sleep/wake key.

Image 68 starts the Wi-Fi milestone selected from the remaining list.

## In scope

- Enable networking/WLAN/cfg80211 and `brcmfmac` SDIO support.
- Add the BCM4329 SDIO controller, 1.8V fixed WLAN rail, reset pwrseq and
  host-wake IRQ to the GPU base DT.
- Add the minimum SDIO2/GPIO pinmux needed by that controller.
- Stage the known Xoom `bcmdhd_sta.bin` firmware under the brcmfmac filename
  (SHA-256 `462e89e7...f5ea7`) plus an empty NVRAM placeholder.
- Add `/sys/class/net`, `/proc/net/dev` and firmware listings to the display
  report.

This is the **kernel/SDIO bring-up image**, not working Android Wi-Fi. The
Android supplicant, DHCP and settings integration are deliberately later.

## Image identity

- Path: `artifacts/androidgpu68-ready/wingray-android44-gpu.img`
- Size: 4,022,272 bytes
- SHA-256: `8944fd2fcae98ad9d5eb2ce8d71a2eb37fa2dd5a6dabc3f76c82dc61bd188a9a`
- Kernel patch: `0122-wingray-bcm4329-sdio.patch`

## Hardware test

Flash boot only:

```sh
fastboot flash boot artifacts/androidgpu68-ready/wingray-android44-gpu.img
fastboot reboot
```

Then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu68-report1 \
  --storage-mode android44-readonly
```

Look for:

- `sdhci` / `mmc1` probe and `brcmfmac` messages in dmesg;
- firmware load success or the exact missing/rejected path;
- `wlan0` in `/sys/class/net` and `/proc/net/dev`;
- the `XOOM_NET` report section;
- no SDIO or pinctrl timeout.

## Failure handling

- No SDIO card: check the `wlan_power`/pwrseq GPIOs, SDIO2 pinmux and
  1.8V rail. The CPCAP `VWLAN1` regulator is not enabled yet, so the fixed
  rail may be unpowered.
- Firmware rejected: the Android `bcmdhd_sta.bin` may not be compatible with
  `brcmfmac`. The next step would be the original bcmdhd/bcm4329 driver or a
  matching brcmfmac 4329 image.
- Boot regression: reflash Image 66.

## Not included

- Android `wpa_supplicant`/DHCP/settings integration.
- Bluetooth.
- Battery/charging/fuel gauge.
- Suspend/resume.
- HWC overlay changes.
