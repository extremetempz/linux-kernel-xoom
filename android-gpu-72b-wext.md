# Image 72b: WEXT-capable wpa_supplicant

25 October 2026. 72a proved the ROM's supplicant lacks WEXT:

```text
Initializing interface 'wlan0' ... driver 'wext'
wlan0: Unsupported driver 'wext'
```

The stable 2.6 driver already has working WEXT; only userspace was missing.
Image 72b builds a WEXT-capable supplicant from the AOSP
`wpa_supplicant_8` android-4.4.4 source with NDK r10e:

- `CONFIG_DRIVER_WEXT=y`
- Android global control socket (`@android:wpa_wlan0`)
- Android logcat output
- internal crypto, no EAP/WPS/P2P/AP
- stripped: 198,032 bytes
- packaged at `/bin/wpa_supplicant-wext`

The kernel built-in initramfs is XZ-compressed to keep the boot image under
the fastboot limit (4,038,656 bytes). `CONFIG_RD_XZ=y`; `CONFIG_RD_GZIP` is
disabled.

## Image identity

- Path: `artifacts/androidgpu72b-ready/wingray-android44-gpu.img`
- Size: 4,038,656 bytes
- SHA-256: `2aa6f9528a288bf214947533eee9db049490798052a4a9837f448a309d627f0c`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu72b-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu72b-report1 \
  --storage-mode android44-readonly
```

Expected:

1. `wpa_supplicant` log says `driver 'wext'` and does **not** say
   `Unsupported driver`.
2. `wlan0` is up; WEXT scan/association starts.
3. `WPA_LOGCAT` shows the WEXT driver init.

Recovery: 70t or Image 66.
