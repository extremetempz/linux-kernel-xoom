# Image 70l: bcmdhd module name and the firmware that actually boots

25 October 2026. 70j proved the private 5.90.100.410 image was used, but it
did not boot:

```text
sta_fw=private_bin:222310
dhdsdio_write_vars: Download, Upload and compare of NVRAM succeeded.
dhdsdio_htclk: HT Avail timeout (1000000): clkctl 0x50
```

The ROM's original 4.218 firmware does boot. The real Android integration
bug was the module name: the ROM's `libhardware_legacy.so` hardcodes:

```text
/sys/module/bcmdhd/parameters/firmware_path
/vendor/firmware/fw_bcmdhd.bin
```

Our module was named `dhd`, so WifiHW could not open the firmware-path
parameter, SoftapController failed, and WifiHW brought `wlan0` down before
`wpa_supplicant` could set it UP.

Image 70l:
- builds the legacy driver as **`bcmdhd.ko`**;
- provides `/system/lib/modules/bcmdhd.ko` (and a `dhd.ko` alias);
- uses the **ROM's 4.218 `fw_bcmdhd.bin`**, which the chip boots;
- points `/system/etc/wifi/bcmdhd_sta.bin` at it;
- keeps the OOB IRQ, WL_REG_ON GPIO, regulatory, cfg80211, fwpath aliases and
  writable supplicant config.

## Image identity

- Path: `artifacts/androidgpu70l-ready/wingray-android44-gpu.img`
- Size: 4,077,568 bytes
- SHA-256: `5ea3cb67c56804a77126cebb4ac76068e3fc13dc2481ddd1b580f9c964666333`

## Test

```sh
fastboot flash boot artifacts/androidgpu70l-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70l-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `sta_fw=system_4.218:264140`
2. `/sys/module/bcmdhd` and no "Failed to open wlan fw path param"
3. Firmware up; `wlan0` stays UP
4. `wpa_supplicant` starts, scan results appear
5. Association and DHCP/IP
6. Display stable

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
