# Image 67e: route the CPCAP interrupt to the GIC

25 October 2026. Images 67b–67d showed the CPCAP SPI transport working, the
`cpcap-pwrkey` input device present, but **zero** CPCAP parent/nested IRQ
counts and no INTS2/INT2 changes after repeated power-button presses.

The DT node used:

```dts
interrupt-parent = <&lic>;
interrupts = <GIC_SPI 86 IRQ_TYPE_LEVEL_HIGH>;
```

`GIC_SPI 86` is the GIC external-PMU input (Linux IRQ 118, matching
`INT_EXTERNAL_PMU` in the original board code). Pointing that specifier at
the Tegra LIC produced `LIC 86` / Linux IRQ 56 instead — visible in every
report as:

```text
56: 0 0 LIC 86 Level cpcap-m2, cpcap-m2, cpcap1-4
```

The GIC parent is now used, so the node maps to GIC SPI 86 / IRQ 118 as the
original board intended. The base peripheral include is corrected too.

## Retained diagnostics

- CPCAP ON is explicitly unmasked and stale status cleared.
- All four `INTS1..4` and `INT1..4` registers are polled every 20 ms.
- Any change is logged with its bank and value.
- `KEY_POWER` still follows `INTS2` bit 7; the polling fallback remains in
  case the physical interrupt is still not usable.

Kernel patches: `0120-wingray-cpcap-all-irq-banks.patch`,
`0121-wingray-cpcap-gic-parent.patch`

## Image identity

- Path: `artifacts/androidgpu67e-ready/wingray-android44-gpu.img`
- Size: 3,698,688 bytes
- SHA-256: `282815f471130e8b352ef36f7b0ef01beff765c2e1f4569a84696dd5a7d4541d`

## Hardware test

Flash boot only:

```sh
fastboot flash boot artifacts/androidgpu67e-ready/wingray-android44-gpu.img
fastboot reboot
```

At boot, expect the same CPCAP detection and polling registration, but the
report's interrupt line should now be a GIC line for SPI 86, not `LIC 86`.

Press and release the back power button several times. Then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu67e-report1 \
  --storage-mode android44-readonly
```

Expected if the GIC routing was the problem:

```text
CPCAP INTS2=0080
CPCAP power key pressed
CPCAP power key released
```

and the CPCAP GIC interrupt count should increase.

## If all banks remain unchanged

If `INTS1..4` and `INT1..4` all stay at their initial values after multiple
presses, the power button is not reaching the CPCAP register banks being
read. The next step is to identify its actual electrical path (a Tegra GPIO
or a different PMIC input) rather than continuing to remap INTS2.

## Scope

Only the CPCAP power-key foundation. No battery/charging, Wi-Fi, Bluetooth,
suspend or HWC overlay work. Image 66 remains the recovery image.
