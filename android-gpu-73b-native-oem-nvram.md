# Image 73b: native 4.4 driver with the Xoom OEM NVRAM

25 October 2026. 73a is the first image with a stable screen, working Wi-Fi
toggle, native nl80211 supplicant and completed scans. But every scan
returned zero BSSes:

```text
nl80211: Received scan results (0 BSSes)
wl_escan_handler : SCAN COMPLETED: scanned AP count=0
```

73a used the postmarketOS TF101 `nvram_4329.txt`. That NVRAM describes a
TF101 board (`boardtype=0x57e`, its PA tables and `aa5g=1`) and may not
match the Xoom's RF calibration. 73b switches back to the Xoom's own
`/system/etc/wifi/bcm4329.cal` as NVRAM:

```text
nvram=system_cal
```

Everything else is unchanged: native 4.4 `bcmdhd.ko`, late 40s load,
Android's nl80211 supplicant, AOSP `fw_bcm4329.bin`.

## Image identity

- Path: `artifacts/androidgpu73b-ready/wingray-android44-gpu.img`
- Size: 4,204,544 bytes
- SHA-256: `3bda7e50cba26a436dda4993e922e412fd0767c39c872ba3236957389e77949b`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73b-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73b-report1 \
  --storage-mode android44-readonly
```

If scans still return zero APs with the Xoom OEM NVRAM, the remaining issue
is firmware/RF, not Android integration. Recovery: 70t or Image 66.
