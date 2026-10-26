# Wingray power-key failure: transport review and unflashed correction

26 October 2026. The user reports Bluetooth pairing/connection working on 75b;
main records a Sony headset connection while Wi-Fi remained connected. Audio,
factory address and long coexistence validation remain separate milestones.
This change does not flash, rebuild a boot image, alter that artifact or remove
the working volume-down-to-power fallback.

## Reviewed history

The local root repository contains `628db2e`, `db22ae2`, `d80ce52` and
`5834a5d` (the matching revision-acceptance commit; the supplied `5834a6d`
hash does not resolve locally). Their effects are preserved in main's patches
0116–0119, followed by the all-bank polling/GIC changes in 0120/0121.

- `628db2e` adds CPCAP transport, input registration and an ON interrupt
  callback. The first IRQ callback selects the private macro bank
  `irqdata[1], 7`; normal INT2 belongs to the bank-1–4 domain. Later commits
  replace this callback with polling, so this is not the reason current
  polling still sees no changes.
- `5834a5d` accepts a decoded zero revision after a zero-valued identification
  response was described as a working ST 1.0 part. That interpretation was
  not established by an independent register value or bus trace.
- `db22ae2` polls INTS2 bit 7; `d80ce52` unmasks ON and logs INT2/INTS2.
  Polling can observe sense transitions without receiving a GIC interrupt,
  so an incorrect IRQ route alone cannot explain every zero-valued poll.

## Verified source mismatches

The working Motorola/ElementalX reference at
`3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd` uses:

1. `board-stingray-power.c`: CS0, **SPI_MODE_0 with no SPI_CS_HIGH**.
2. `cpcap-regacc.c`: **one 32-bit full-duplex transfer**, packing the command
   in the high half and obtaining the read result from the low half.
3. `cpcap-regbits.h`: ON sense is INTS2 bit 7. That bit selection matches
   the current polling code; changing it at random is not justified.

The port instead forces `SPI_MODE_0 | SPI_CS_HIGH`, requests `spi-cs-high`
in both Wingray CPCAP DT descriptions, and uses split 16-bit command/read
transfers. The Tegra SLINK driver explicitly programs its CS polarity from
SPI_CS_HIGH, so this differs from the original board wiring. Restoring the
original complete transaction also avoids relying on unvalidated behavior
across split SLINK transfers. Split transfers alone are not proven to be a
failure if chip select stays correctly asserted; there is no logic-analyzer
capture establishing which portion of the mismatch dominates.

## Verified saved observations, and what remains uncertain

Private reports from 67b/67c/67d/67e and later 70 variants show decoded
`ST rev: 1.0 (0)`, zero initial interrupt/sense banks and no CPCAP parent
interrupt progress. Registration of `cpcap-pwrkey` proves only software setup;
a successful SPI syscall does not prove a responding PMIC. A zero-valued
response decodes to ST/1.0 through the existing bit-extraction helpers.

The CS polarity mismatch is a concrete defect and the strongest identified
transport-level explanation. **No physical test of this correction has been
performed, so it is not proven that this is the only reason the button fails.**
There is no independently validated raw VERSC1 value from the original ROM
in the reviewed evidence. The new zero/all-ones identity rejection is a
conservative bring-up gate, not a claim that every possible old chip revision
has been exhaustively characterized.

## Separate correction: patch 0141

- On Wingray only, use active-low CS0 and one native 32-bit full-duplex
  transfer matching the original Motorola driver. Existing regmap addresses
  already incorporate the legacy word-address shift; do not shift twice.
- Log the full raw VERSC1 before revision decoding. Reject zero/all-ones
  identities before regmap IRQ setup writes PMIC masks or starts polling.
  Keep the old-revision-field allowance for otherwise plausible identities.
- Remove the active-high CS flag in both Wingray DT descriptions.
- Leave other boards' transport branch, ON bit, current GIC route, Wi-Fi,
  Bluetooth, display, regulators, charging and volume-down mapping alone.

## Offline checks

The actual transfer/setup/identity functions are compiled into a host fixture:
32-bit single full-duplex transfers, command words for VERSC1/INTS2/INTM2,
low-half response extraction, register/value bounds, SPI setup/read failures,
unchanged non-Wingray mode and zero/all-ones identity rejection all pass.

The corrected CPCAP object and Bluetooth-profile DT compile with the pinned
ARM toolchain and 75b configuration. Comparing the compiled DT against the
saved 75b DT shows exactly one delta: removal of
`/spi@7000d400/pmic@0:spi-cs-high`. The existing CPCAP, Bluetooth power,
Bluetooth setup and Wi-Fi fixtures pass. No full kernel link or new boot
image is claimed by this review.

```sh
python3 tests/test-wingray-cpcap-transport.py
python3 tests/test-wingray-cpcap-key.py
python3 tests/test-wingray-bluetooth-power.py
python3 tests/test-wingray-bluetooth-setup.py
python3 tests/test-wingray-wifi.py
```

## Next physical gate, when authorized and scheduled

Keep the working 75b and volume-down fallback. In a separate boot-only test,
first obtain a stable, non-idle raw VERSC1 identity and inspect ON sense while
holding/releasing the actual button. If the new guard rejects the identity,
stop changing input bits or IRQs and check CS0/MISO/clock/pinmux against the
original working ROM. If sense transitions work, verify evdev KEY_POWER
press/release, then Android screen behavior. Repair the IRQ domain/handler
separately before claiming wake-from-suspend; polling plus wakeup-capable
registration does not establish a working suspend wake source.

Original GPL sources:
[Motorola SPI board setup](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/arch/arm/mach-tegra/board-stingray-power.c),
[register-access transport](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/drivers/mfd/cpcap-regacc.c).
