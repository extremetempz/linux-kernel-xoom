> **Superseded by Image 70o.** 70m tolerated preinit but supplicant still
> failed interface UP; 70o adds NET_ADMIN/NET_RAW and debug. Use
> `android-gpu-70o-bcmdhd-legacy.md`.

# Image 70m: keep wlan0 up when old firmware lacks optional iovars

25 October 2026. Image 70l fixed the biggest Android mismatch:

- module is now `bcmdhd`, so WifiHW/SoftapController find
  `/sys/module/bcmdhd/parameters/firmware_path`;
- **`Softap fwReload - Ok`** appears in logcat;
- the ROM 4.218 firmware boots and reports a MAC.

But `dhd_open` still failed and tore the interface down:

```text
Firmware version = ... 4.218.248.44
get chanspecs failed with -23
wl_update_wiphybands ... fails err=-23
wl_android_wifi_off in
wpa_supplicant: wlan0: Failed to initialize driver interface
```

The 4.218 dongle firmware predates several optional preinit iovars in the
newer 5.90 host driver.  `dhd_dev_init_ioctl()` returned `-23`, so
`wl_android_wifi_on()` set `-EFAULT`, `dhd_open()` failed, Android brought
`wlan0` down, and supplicant could not open it.

Image 70m logs the optional preinit failure and **continues** instead of
failing the interface. The required firmware boot, OOB IRQ, WL_REG_ON and
WifiHW module paths are already in place.

## Image identity

- Path: `artifacts/androidgpu70m-ready/wingray-android44-gpu.img`
- Size: 4,077,568 bytes
- SHA-256: `3000d0fe27e21ac088f63e0ffee527389d69c191a853bcbc3065ddce767e7a97`

## Test

```sh
fastboot flash boot artifacts/androidgpu70m-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70m-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `Softap fwReload - Ok`, no fw-path error.
2. Firmware up and `wlan0` remains UP.
3. `wpa_supplicant` does not report “Failed to initialize driver interface”.
4. Scan results, association and DHCP/IP.
5. Display stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
