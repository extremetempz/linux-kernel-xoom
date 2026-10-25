> **Superseded by Image 72d.** 72c initialized WEXT but the kernel lacked
> AF_PACKET and the supplicant lost CAP_NET_ADMIN. Use
> `android-gpu-72d-wext.md`.

# Image 72c: register the WEXT driver in wpa_supplicant

25 October 2026. 72b proved the custom WEXT supplicant was present but
reported:

```text
No drivers enabled
Failed to initialize wpa_supplicant
```

The binary had `driver_wext.o` linked but the driver table was compiled
without `CONFIG_DRIVER_WEXT`, so `wpa_drivers[]` was empty.

72c rebuilds the AOSP 4.4 supplicant with **`-DCONFIG_DRIVER_WEXT`**
explicitly in CFLAGS. The table now contains the WEXT driver.

Also, the image's external empty ramdisk is now XZ, matching the kernel's
XZ built-in initramfs, so the old `compression method gzip not configured`
warning is gone.

## Image identity

- Path: `artifacts/androidgpu72c-ready/wingray-android44-gpu.img`
- Size: 4,044,800 bytes
- SHA-256: `6be54c3154337bd44b76ccc6aaacb942fa375f8fe5f6e3a82f1209fc7e4aa593`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu72c-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu72c-report1 \
  --storage-mode android44-readonly
```

Expected `WPA_LOGCAT`:

```text
Initializing interface 'wlan0' ... driver 'wext'
```

with no `No drivers enabled` and no `Unsupported driver`.

Recovery: 70t or Image 66.
