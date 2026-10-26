# Power-button candidate 77 — CPCAP on SPI2

26 October 2026. **Physical result: screen flicker fixed; power button still
not working.** The controller mapping was real and necessary, but CPCAP still
returns `VERSC1=0000` and all ON-sense banks are zero. See
[the detailed 77 findings](docs/power-key-77-findings.md).

## Confirmed mapping error

Motorola's original board registers CPCAP with `bus_num = 1`. In the original
Tegra device table that is `tegra_spi_device2` (`.id = 1`) at
**SPI2, 0x7000d600**, using the SPI2 pin group (SPIA/SPIB/SPIC/SPIG).

The port bound CPCAP to `spi@7000d400` (SPI1, `.id = 0`) and forced the
SPID/SPIE/SPIF SPI1 pins. The `spi1` DT alias also pointed at 0x7000d400.
That explains both the earlier zero CPCAP replies and why changing only the
transfer format disturbed the display.

## 77 correction

- CPCAP moved to `spi@7000d600`
- `spi1` alias corrected to `/spi@7000d600`
- Pinmux changed to SPIA/SPIB/SPIC/SPIG, function `spi2`, matching Motorola's
  original pin table
- SPI1 (`0x7000d400`) left disabled
- active-low CS0 and native32 full-duplex transfer retained
- identity guard remains non-fatal for diagnostics

## Image identity

- Path: `artifacts/androidpower77-ready/wingray-android44-gpu.img`
- Size: 4,128,768 bytes
- SHA-256: `ab3f4bbd3cd29ae16863782c5dfdb1b280d18c11d3a0123c60528f0128f5b889`
- Profile: Bluetooth 75b + corrected CPCAP SPI2

## Checks

```text
PASS actual CPCAP functions
PASS CPCAP power-key transport/config/DT scope
PASS Bluetooth power callback
PASS Bluetooth setup wait/retry
PASS native bcmdhd Wi-Fi
PASS compiled Bluetooth DT and configuration
```

The compiled DT now has the CPCAP node under `spi@7000d600`, the SPI2 pin
group, and `spi@7000d400` disabled.

## Remaining blocker

`cpcap-pwrkey` is registered and polling, but the sense bit never transitions;
the CPCAP parent IRQ is later disabled as "nobody cared". The next controlled
test is CS polarity on the corrected SPI2 bus, then split-16-bit framing, one
variable at a time.

## Flash and test (for reference only)

Restore 75b first if needed. Then:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidpower77-ready/wingray-android44-gpu.img
fastboot reboot
```

Watch the screen before testing the power button. If stable, capture:

```sh
python3 scripts/capture-framed-diagnostic.py   --output-dir artifacts/androidpower77-report1   --storage-mode android44-readonly
```

Look for:

```text
Wingray CPCAP VERSC1=....
CPCAP vendor: ST rev: 1.0 (0)
CPCAP power key pressed
CPCAP power key released
```

If it still flickers, stop and restore 75b. Do not continue changing PMIC
writes. The CPCAP GIC IRQ path/wake-from-suspend remain separate work.
