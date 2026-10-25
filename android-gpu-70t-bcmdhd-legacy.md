> **Superseded by Image 70v.** 70t still used the 2.6 5.90.195 host driver.
> Use `android-gpu-70v-bcmdhd-tf101.md`.

# Image 70t: same PMOS firmware+NVRAM, small enough for fastboot

25 October 2026. The 70s boot image was 4,429,824 bytes and fastboot rejected
it before sending:

```text
Sending 'boot' (0 KB) FAILED (File is too large to download)
```

The Xoom bootloader has a limited fastboot download size.  The build did not
need to embed the AP firmware in the initramfs for station Wi-Fi, so 70t drops
the 267,027-byte AP image from the boot image while keeping:

- AOSP `fw_bcm4329.bin` (246791) for station
- postmarketOS `nvram_4329.txt` as NVRAM (`nvram=postmarketos_4329`)
- `bcmdhd` module, OOB IRQ, WL_REG_ON, wpa wrapper
- AP firmware remains available from the ROM at runtime if Softap needs it

## Image identity

- Path: `artifacts/androidgpu70t-ready/wingray-android44-gpu.img`
- Size: 4,247,552 bytes
- SHA-256: `1524e1f54a50950060ee9398342c0cbbf83f525495f0baafb386b72b8c1c69b7`

## Flash from the repository root

Use the absolute path if the current directory is uncertain:

```sh
cd /home/justin/linux-kernel-xoom
fastboot getvar max-download-size
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70t-ready/wingray-android44-gpu.img
fastboot reboot
```

Then open Settings → Wi-Fi, connect, and capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70t-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `sta_fw=aosp_246791:246791`, `nvram=postmarketos_4329`
2. Firmware up without chanspec/preinit abort
3. `/run/wpa.log` driver init and scan
4. Association and DHCP/IP
5. Display stable

Image 66 remains the recovery image.
