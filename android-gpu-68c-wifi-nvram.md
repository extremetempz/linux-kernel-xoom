> **Superseded by Image 68d.** The NVRAM loaded, but the bcmdhd firmware
> did not boot under brcmfmac (`HT Avail timeout`). Image 68d stages the
> matching brcmfmac 4329 firmware. Use `android-gpu-68d-wifi-firmware.md`.

# Image 68c: BCM4329 NVRAM for brcmfmac

25 October 2026. Image 68b fixed the SDIO voltage and reached the chip:

```text
mmc1: new SDIO card at address 0001
brcmfmac: brcmf_sdio_drivestrengthinit: No SDIO Drive strength init done for chip 4329 rev 3
```

The next failure was the empty NVRAM placeholder:

```text
firmware, attempted to load /lib/firmware/brcm/brcmfmac4329-sdio.txt, but failed with error -22
Direct firmware load for brcm/brcmfmac4329-sdio.txt failed with error -22
brcmf_sdio_htclk: HT Avail timeout (1000000): clkctl 0x50
```

brcmfmac requires a non-empty NVRAM image. Image 68c stages a minimal one:

```text
macaddr=02:00:00:00:00:01
```

## Image identity

- Path: `artifacts/androidgpu68c-ready/wingray-android44-gpu.img`
- Size: 4,024,320 bytes
- SHA-256: `66a0711092f054d4825eddef25c2414a556e5e2ee07c8037cfa918517e3f2902`

Only the runtime NVRAM content changed from 68b.

## Hardware test

```sh
fastboot flash boot artifacts/androidgpu68c-ready/wingray-android44-gpu.img
fastboot reboot
```

Capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu68c-report1 \
  --storage-mode android44-readonly
```

Look for:

- NVRAM load success instead of `-22`;
- the firmware `.bin` download result;
- `wlan0` in `/sys/class/net`;
- the `XOOM_NET` section.

## Expected next failure

If the bcmdhd firmware is rejected by brcmfmac, the report will identify the
failure. The next step would be a matching brcmfmac 4329 firmware or the
original bcmdhd/bcm4329 driver.

Android `wpa_supplicant`/DHCP/settings are still not integrated. Image 66
remains the recovery image.
