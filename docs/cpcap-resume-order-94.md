# CPCAP IRQ resume ordering — Image 94

## Fix

The CPCAP parent IRQ was still enabled while its SPI controller was
suspended. During resume the regmap-irq parent handler ran before SPI was
usable and produced thousands of:

```text
cpcap-core spi32766.0: Failed to read IRQ status: -108
```

Image 94 masks the parent IRQ for the duration of the system-sleep
suspend/resume pair:

- `cpcap_wingray_pm_suspend()` arms the LIC wake reference first, then
  `disable_irq(cpcap->spi->irq)` before the SPI parent suspends.
- `cpcap_wingray_pm_resume()` calls `enable_irq()` after the SPI parent has
  resumed, then releases the wake reference.
- The LIC wake mask remains armed through `enable_irq_wake()`, so the physical
  ON power button is intended to remain a wake source.
- New markers:
  `WG_PM94_CPCAP_SUSPEND ... irq_masked=1`,
  `WG_PM94_CPCAP_RESUME ... irq_masked=0`.
- The LP2 status helper now reports
  `LP2TEST_CPCAP_IRQ_ERRORS <count>` so the flood can be checked directly.

## Image

`artifacts/lp2g-ready/wingray-android44-gpu.img`

- 4,220,928 bytes
- SHA-256 `0b94d2117435b9df7b6a59b27a333b6fb3b3e2b69d649ee608f8ac6be0ce1328`
- Not flashed; physical wake with the parent IRQ masked is not yet proven.

## Critical test

This test has a real physical-wake risk: if masking the parent IRQ also masks
the LIC wake path, the power button will not wake the tablet.

1. Flash Image 94.
2. Confirm pre-test boot ID and `XOOM_PM_TEST none`.
3. Trigger one LP2 request.
4. Press the physical power button once.
5. If it does not wake within 30 seconds, force power-cycle, flash Image 93e,
   and stop. Do not repeat blindly.
6. If it wakes, run `--status` and verify:
   `LP2TEST_CPCAP_IRQ_ERRORS 0`,
   `WG_PM94_CPCAP_SUSPEND ... irq_masked=1`,
   `WG_PM94_CPCAP_RESUME ... irq_masked=0`,
   plus the `WG_LP2_*` markers and same boot.

Only after this passes should repeated LP2 cycles and power measurement begin.
