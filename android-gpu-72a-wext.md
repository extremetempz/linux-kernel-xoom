# Image 72a: WEXT fallback with the stable 2.6 driver

25 October 2026. The TF101 cfg80211 path keeps failing at supplicant driver
init even though `wlan0` and firmware are up. 71e's station no-op did not
change:

```text
nl80211: Set mode ifindex 3 iftype 2 (STATION)
wlan0: Failed to initialize driver interface
```

Image 72a changes integration approach instead of patching cfg80211 again:

- stable 2.6 bcmdhd driver (screen-safe)
- WEXT (`wl_iw.o`) compiled in
- `wpa_supplicant -Dwext` instead of `-Dnl80211`
- AOSP `fw_bcm4329.bin` and PMOS `nvram_4329.txt`
- bcmdhd module, preload and `wlan0` up
- logcat capture remains

This bypasses the broken cfg80211/nl80211 path entirely. If the ROM's
`wpa_supplicant` binary has no WEXT driver, `WPA_LOGCAT` will say
`Unsupported driver 'wext'` and this approach is dead too.

## Image identity

- Path: `artifacts/androidgpu72a-ready/wingray-android44-gpu.img`
- Size: 4,276,224 bytes
- SHA-256: `01a16e90eb1acb676f61c2efa496bde8723decc291ec3485d3d63e1d32f8ac59`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu72a-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu72a-report1 \
  --storage-mode android44-readonly
```

Recovery remains 70t or Image 66.
