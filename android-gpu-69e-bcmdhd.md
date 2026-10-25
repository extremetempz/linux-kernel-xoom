> **Superseded by Image 69f.** 69e reached SDIO probe but the donor driver
> rejected chip 0x4329. Use `android-gpu-69f-bcmdhd.md`.

# Image 69e: make bcmdhd actually register the SDIO function

25 October 2026. Image 69d loaded `dhd.ko` successfully:

```text
insmod_rc=0
DHD_MODULE present
dhd_module_init in
dhd_module_init out
```

but there was no SDIO probe and no `wlan0`. The root cause is the driver's
`CONFIG_DTS` build path:

- `dhd_wifi_platform_register_drv()` registered a platform driver for an
  `android,bcmdhd_wlan` device node and returned success.
- This board has no such node, so the platform probe never ran and
  `dhd_bus_register()`/the SDIO client driver were never registered.

Image 69e builds bcmdhd **without `CONFIG_DTS`**. The non-DT path falls
through to `dhd_wifi_platform_load()` and `dhd_bus_register()`, which
registers the SDIO driver against the already-enumerated `mmc1:0001:1`
BCM4329 function. An unconditional `linux/of_gpio.h` include fixes the
remaining non-DTS compile dependency.

Kernel patches: `0127-wingray-bcmdhd-no-dts.patch`,
`0128-wingray-bcmdhd-of-gpio.patch`.

## Image identity

- Path: `artifacts/androidgpu69e-ready/wingray-android44-gpu.img`
- Size: 4,288,512 bytes
- SHA-256: `c9326d5f9981ef7364160bde64e22ac5b05a2de2f27701327f1514a64ff00635`

## What should change

The dmesg should now show a real SDIO probe after `dhd_module_init in`:
firmware download, chip detection, `wlan0` creation, and then the Android
supplicant/DHCP path.

## Test

```sh
fastboot flash boot artifacts/androidgpu69e-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, try to connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu69e-report1 \
  --storage-mode android44-readonly
```

## Verification criteria

1. `dhd_module_init` reaches SDIO probe and firmware download.
2. `wlan0` appears in `XOOM_NET`.
3. `wpa_supplicant` starts.
4. Actual association and IP configuration.

Image 66 remains the clean recovery image. Power key remains parked;
volume-down is the working wake key.
