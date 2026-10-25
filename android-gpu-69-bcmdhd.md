> **Superseded by Image 69b.** 69b uses a clean Android 4.4 supplicant
> socket config and adds Wi-Fi state diagnostics. Use
> `android-gpu-69b-bcmdhd.md`.

# Image 69: Xoom bcmdhd 4329 module and Android Wi-Fi services

25 October 2026. Image 68e enumerated the BCM4329 SDIO card with brcmfmac
but never created `wlan0`, and the Android ROM is built around the bcmdhd
stack (`fw_bcmdhd.bin`, `bcm4329.cal`, WifiHW/softap firmware reload).

Image 69 switches to the 4.4-native donor bcmdhd driver, configured for the
4329/4330 family.  The module metadata advertises the 4329 SDIO ID:

```text
alias=sdio:c*v02D0d4329*
```

## Changes

- `brcmfmac` disabled; donor `bcmdhd` built as `dhd.ko` with `BCM4330`
  chip support.
- Firmware and NVRAM paths:
  - `/system/vendor/firmware/fw_bcmdhd.bin`
  - `/system/etc/wifi/bcm4329.cal`
- Module is stripped of debug symbols (about 1.0 MiB) and packed at
  `/lib/modules/dhd.ko`.
- `xoomwifi` post-fs-data service waits for `/system`, creates the Wi-Fi
  data directories, copies the supplicant config, and runs `insmod`.
- Android `wpa_supplicant` and `dhcpcd` services are defined.
- Screen-awake service remains `xoomawake`; volume-down wake remains.
- One 4.4 cfg80211 API fix: removed `wiphy->wowlan` assignment.

Kernel patches: `0125-wingray-bcmdhd-module.patch`,
`0126-wingray-bcmdhd-44-api.patch`.

## Image identity

- Path: `artifacts/androidgpu69-ready/wingray-android44-gpu.img`
- Size: 4,288,512 bytes
- SHA-256: `c681e16dd213deee96bdee8eb53986b606a2f590687dcb71952bc7219f979356`

This image is **not declared Wi-Fi-ready** until the hardware report shows
`wlan0`, supplicant startup and an actual association.

## Hardware test

```sh
fastboot flash boot artifacts/androidgpu69-ready/wingray-android44-gpu.img
fastboot reboot
```

After boot, open Settings → Wi-Fi and try to connect to a network.  Then
capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu69-report1 \
  --storage-mode android44-readonly
```

Check:

- `/run/xoom-wifi.log` for `insmod_rc`;
- dmesg for `dhd`, firmware download, `wlan0`;
- `XOOM_NET` for `wlan0`;
- supplicant/dhcp/service logs;
- an actual association/IP address.

## Failure handling

- `insmod_rc` nonzero: module dependency/vermagic or missing firmware path.
- module loads, no `wlan0`: bcmdhd firmware/calibration or 4329-vs-4330
  chip configuration.
- `wlan0` exists but WifiHW fails: Android framework expects the module at
  `/system/lib/modules`; the next step is a module-path/framework shim.

Recovery image remains Image 66.  Power key remains parked; volume-down is
the working sleep/wake key.
