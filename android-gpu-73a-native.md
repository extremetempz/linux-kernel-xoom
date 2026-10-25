> **Superseded by Image 73b.** 73a was stable and scanned but returned
> zero BSSes with the PMOS TF101 NVRAM. Use
> `android-gpu-73b-native-oem-nvram.md`.

# Image 73a: native 4.4 bcmdhd, loaded late

25 October 2026. The custom 2.6 + WEXT route ended in a freeze on the Wi-Fi
screen; 72f's standard scan handler is reverted. This is a different route:

- the **native 4.4 bcmdhd driver** from the Decatf tree
- module renamed `bcmdhd.ko` for the ROM HAL
- loaded **40 seconds after boot**, after display/SDIO are settled
- Android's own `/system/bin/wpa_supplicant -Dnl80211`
- AOSP BCM4329 firmware and postmarketOS NVRAM
- no WEXT, no custom supplicant

This driver previously booted firmware and created `wlan0`, but flashed the
screen when loaded at 2.8s. The late load is intended to avoid that.

## Warning

If the screen flashes, stop and restore 70t immediately. This is the last
display-risk test.

## Image identity

- Path: `artifacts/androidgpu73a-ready/wingray-android44-gpu.img`
- Size: 4,200,448 bytes
- SHA-256: `c44745b20d029a0116a883b5f4eaff16e4b10c41df27b9da2d36a241b4668c5b`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73a-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73a-report1 \
  --storage-mode android44-readonly
```

Check screen first. If stable, check `wlan0`, native supplicant and scan.

Recovery: 70t or Image 66.
