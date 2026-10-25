> **Superseded by Image 70h.** 70g still fell back to the 4.218 firmware
> at `/system/etc/wifi/bcmdhd_sta.bin`. Use
> `android-gpu-70h-bcmdhd-legacy.md`.

# Image 70g: match the 2.6 driver to the Xoom firmware and WL_REG_ON

25 October 2026. Image 70f proved the OOB path works:

- GPIO 165 is registered as `bcmsdh_sdmmc`, active-high.
- Firmware boots and reports a MAC.
- `wpa_supplicant` starts.

But it used the ROM's `fw_bcmdhd.bin`:

```text
Firmware version = wl0: May 25 2012 ... version 4.218.248.44
CFG80211-ERROR) wl_construct_reginfo : get chanspecs failed with -23
CFG80211-ERROR) wl_update_wiphybands : wl_construct_reginfo() fails err=-23
```

The imported 2.6/ElementalX host driver is version **5.90.195.114** and
expects the matching Xoom firmware, not the old 4.218 ROM image. The private
ROM-reference firmware is:

- `artifacts/hardware-private/wifi/bcmdhd_sta.bin`
- size 222,310
- version **5.90.100.410**
- SHA-256 `462e89e7bcf1f4fd701933d9cb80e795acca27a7c80300e42661d7e3bc6f5ea7`

Image 70g stages that firmware in `/lib/firmware/bcmdhd_sta.bin` and copies
it to `/system/etc/wifi/bcmdhd_sta.bin` for the driver.

It also implements the second missing 2.6 board callback: `wifi_set_power`
now drives **WL_REG_ON/reset on GPIO U2**. Without it, the first failed open
left the chip in reset and every retry failed with `ChipClkCSR` reads of 0.

## Image identity

- Path: `artifacts/androidgpu70g-ready/wingray-android44-gpu.img`
- Size: 4,220,928 bytes
- SHA-256: `3084f57c1a210e5084a905d58e40067bee3308be319e399fc8920748854cb4f2`

## Test

```sh
fastboot flash boot artifacts/androidgpu70g-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70g-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. Firmware reports version 5.90.100.410.
2. No `get chanspecs failed` / `wl_update_wiphybands` abort.
3. `wpa_supplicant` brings `wlan0` up and scan results appear.
4. Association and DHCP/IP.
5. Display remains stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
