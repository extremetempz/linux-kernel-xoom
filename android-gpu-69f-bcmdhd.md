> **Superseded by Image 69g.** 69f downloaded firmware but the 4330-only
> debug validator rejected the runtime 4329. Use
> `android-gpu-69g-bcmdhd.md`.

# Image 69f: accept the BCM4329 chip in bcmdhd

25 October 2026. Image 69e reached the SDIO probe, then stopped with:

```text
bcmsdh_sdmmc: bcmsdh_sdmmc_probe Enter
sdioh_attach: sd clock rate = 25000000
sdioh_cis_read: func_cis_ptr[0]=0x1000
dhdsdio_probe_attach: unsupported chip: 0x4329
dhdsdio_probe: dhdsdio_probe_attach failed
sdioh_probe: bcmsdh_probe failed
bcmsdh_sdmmc: probe of mmc1:0001:2 failed with error -12
```

The donor driver advertised the 4329 SDIO device ID but omitted
`BCM4329_CHIP_ID` from `dhdsdio_chipmatch()`. Image 69f adds it, allowing
the existing generic SDIO/ARM/SOCRAM firmware path to run against the Xoom
chip.

Kernel patch: `0129-wingray-bcmdhd-4329-chip.patch`.

## Image identity

- Path: `artifacts/androidgpu69f-ready/wingray-android44-gpu.img`
- Size: 4,288,512 bytes
- SHA-256: `efac6b996542253f5d745fbdeacfc4bd91b3c0a812e16d4d7b51f9cb29f4b958`

## Expected next log

After `bcmsdh_sdmmc_probe Enter`, the driver should pass the chip check,
find the ARM/SOCRAM cores, download `fw_bcmdhd.bin`, and create `wlan0`.

## Test

```sh
fastboot flash boot artifacts/androidgpu69f-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, try to connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu69f-report1 \
  --storage-mode android44-readonly
```

## Verification criteria

1. SDIO probe passes `dhdsdio_chipmatch` and reaches firmware download.
2. `wlan0` appears in `XOOM_NET`.
3. `wpa_supplicant` starts.
4. Actual association and IP configuration.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
