> **Superseded by Image 68e.** Image 68d enumerated the card with matching
> firmware but never created `wlan0`, and the init service name was still
> invalid. Image 68e fixes the service name, tries the fullmac-4 firmware,
> and reports the on-device Wi-Fi/NVRAM files. Use
> `android-gpu-68e-wifi-nvram-files.md`.

# Image 68d: matching brcmfmac BCM4329 firmware

25 October 2026. Image 68c fixed the NVRAM parse; the SDIO card enumerated
and brcmfmac recognized the chip:

```text
mmc1: new SDIO card at address 0001
brcmfmac: brcmf_sdio_drivestrengthinit: No SDIO Drive strength init done for chip 4329 rev 3
```

but the bcmdhd firmware did not boot:

```text
brcmf_sdio_htclk: HT Avail timeout (1000000): clkctl 0x50
```

Image 68d replaces the Android `bcmdhd_sta.bin` with the matching
`brcmfmac4329-sdio.bin` from the host linux-firmware package:

- SHA-256: `d61983946b1e733e4c75dbe6841ac0f1250ebed2e3ee9058cdfdbbba3ba37c93`
- NVRAM remains `macaddr=02:00:00:00:00:01`

## Image identity

- Path: `artifacts/androidgpu68d-ready/wingray-android44-gpu.img`
- Size: 4,055,040 bytes
- SHA-256: `ec66766723e6539f28291a0e52b0d609560b2636075a8b3323371eab8c7aa5a2`

Only the runtime firmware changed from 68c.

## Hardware test

```sh
fastboot flash boot artifacts/androidgpu68d-ready/wingray-android44-gpu.img
fastboot reboot
```

Capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu68d-report1 \
  --storage-mode android44-readonly
```

Look for:

- firmware download and clock-availability success;
- `wlan0` in `/sys/class/net`;
- `XOOM_NET` showing wlan0;
- no repeated `HT Avail timeout`.

## If HT timeout persists

The remaining suspects are the SDIO clock/power sequence and required
board NVRAM parameters, not the firmware filename. The report will show
whether firmware download completed before the timeout.

Android `wpa_supplicant`/DHCP/settings are still not integrated. Image 66
remains the recovery image.
