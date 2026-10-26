# Power-button candidate 78 — CS-high on corrected SPI2

26 October 2026. **Built and checked; not flashed or hardware validated.**

Image 77 fixed the screen flicker with CPCAP on the correct SPI2 controller,
but CPCAP still returned `VERSC1=0000` and all ON-sense banks were zero.
Candidate 78 changes only the next variable: **chip-select polarity on the
correct SPI2 bus**.

- keeps CPCAP on `spi@7000d600` and SPI2 pins
- restores `spi-cs-high` / `SPI_MODE_0 | SPI_CS_HIGH`
- keeps native32 framing and the non-fatal identity diagnostic
- unchanged Android key mapping and polling intervals

Motorola's original board data says active-low CS with mode 0, but the stable
4.4 image previously ran CS-high. This build isolates that single difference
on the now-correct controller.

## Image identity

- Path: `artifacts/androidpower78-ready/wingray-android44-gpu.img`
- Size: 4,128,768 bytes
- SHA-256: `e8a698405f65b9a6b408d66bbf864662bf9830cdc155670d4808474f60dee49d`

## Checks

```text
PASS actual CPCAP functions
PASS CPCAP power-key transport/config/DT scope
PASS Bluetooth power callback
PASS Bluetooth setup wait/retry
PASS native bcmdhd Wi-Fi
PASS compiled Bluetooth DT and configuration
```

## Test — screen first, then button

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidpower78-ready/wingray-android44-gpu.img
fastboot reboot
```

Watch for flicker before touching the back power button. If stable, capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidpower78-report1 \
  --storage-mode android44-readonly
```

Success criteria:

```text
Wingray CPCAP VERSC1=....      # non-zero
CPCAP power key pressed
CPCAP power key released
```

If `VERSC1` is still zero, the next isolated variable is split-16-bit framing
on the same SPI2 controller and CS setting. If it flickers, restore 75b.
