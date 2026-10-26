# CPCAP SPI2 candidate 77 — findings

26 October 2026. Image 77 fixed the screen flicker by moving CPCAP to the
original SPI2 controller and SPI2 pins. The physical power button still does
not work. No new image was flashed for this analysis.

## Confirmed by the report

```text
spi@7000d600: okay, CPCAP child, SPI2 pins
spi@7000d400: disabled
input: cpcap-pwrkey ... 7000d600.spi ...
```

- Display/backlight are stable: the controller/pin correction fixed the
  regression caused by writing through SPI1.
- CPCAP still returns an all-zero identity:

```text
cpcap-core spi32766.0: Wingray CPCAP VERSC1=0000
cpcap-core spi32766.0: Unvalidated CPCAP identity; continuing for diagnostics
cpcap-core spi32766.0: CPCAP vendor: ST rev: 1.0 (0)
```

- All sense/status banks are zero:

```text
CPCAP power key initial INTS1..4=0000
CPCAP power key initial INT1..4=0000
```

- `cpcap-pwrkey` is registered, but polling never sees
  `CPCAP_BIT_ON_S`, so no `KEY_POWER` press/release is emitted.
- The CPCAP parent IRQ is not healthy:

```text
irq 58: nobody cared (try booting with the "irqpoll" option)
Disabling IRQ #58
```

The IRQ is disabled after the spurious storm; polling continues independently.

## What this rules in and out

- **Not the DT controller address anymore**: SPI2/0x7000d600 is correct and
  stable.
- **Not Android key mapping**: `cpcap-pwrkey` exposes KEY_POWER; the input
  device exists.
- **Not the 20 ms polling timer**: it runs, but the sense bit is always zero.
- **Transport is still not receiving a valid CPCAP reply** on the now-correct
  bus. The remaining variables are:
  1. CS polarity (`spi-cs-high` / `SPI_CS_HIGH`) on SPI2
  2. device/transfer word size and framing (`bits_per_word`, 16 vs 32,
     split vs full-duplex)
  3. SPI2 pin/clock/CS mapping or board-level CS wiring
  4. CPCAP IRQ line/status path, separate from polling

## Recommended next controlled tests

Do not change PMIC writes and bus properties together again.

1. **SPI2 + CS-high only**: keep split/native32 and correct controller, but
   set `spi-cs-high`/`SPI_CS_HIGH`; screen first, then check VERSC1.
2. If still zero, **SPI2 + split-16-bit only** with the previously stable CS
   setting.
3. If still zero, stop flashing and probe SPI2 CS/clock/MISO against the
   original ROM with a logic analyzer, or use a read-only SPI test that does
   not write PMIC registers.
4. Only after a non-zero VERSC1 and ON-sense transition should the IRQ path
   and Android key handling be revisited.

The working power fallback is the volume-down KEY_POWER mapping. The stable
75b Bluetooth/Wi-Fi image remains the recovery baseline.
