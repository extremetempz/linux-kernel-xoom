# Image 27: shared panel supply and I2C readiness

Prepared 21 October 2026. This continues image 26's physically verified USB,
full eMMC capacity and all ten BigPart partition extents. It does not attempt
Android startup or change the on-disk layout.

## Why isolate this stage

The existing broad peripheral profile has not been hardware-tested. Reviewing
the original P3 board and backlight sources found two relevant differences:

- PB2 is the shared 5 V panel/LVDS supply with a 200 ms startup delay. The source
  explicitly records its I2C signal-level dependency for the backlight and touch.
  PD0 backlight gating is used in the pre-P1 path, not the P3 LP8550 path.
- P3 selects device control configuration `0x02`, writes it with enable bit 0
  set (`0x03`), and scales brightness into register A0 to limit LED current.
  The current generic LP855x path writes brightness register 00. Merely changing
  the DT control byte would not reproduce the original P3 brightness behavior.

These are source findings, not the proven cause of a display failure. The broad
profile remains unvalidated. Avoid enabling it before resolving this difference.

Read-only working-ROM metadata confirms its `tegra_fb` 1280x800 framebuffer,
32-bit pixels and 1280x1600 virtual size. At capture time backlight brightness
was zero and the display clocks were off. The clock tree recorded PLL_C at
598 MHz with disp1 parented to it; this is not an active scanout measurement.
Raw clock/backlight evidence stays private.

## Minimum test

Patch 0045 / donor commit `e3ea2b29` adds `wingray_panelbus_defconfig` and a
separate DT, based directly on the tested diagnostic DT/config. It retains
UP, memory reservations, USB GPIOs/PHY, eMMC, scoped capacity and GPT/BigPart
fixes. Cookie is `0x584d001b`.

Only add the PB2 fixed supply (boot-on/always-on, 5 V, 200 ms), I2C1 adapter and
character device, and the two working-board I2C1 pin groups (SPDI/SPDO). No I2C
clients or backlight driver are registered. DRM/display, touch, CPCAP, CPU rails,
Wi-Fi, suspend and DVFS remain disabled. The fixed rail retains panel power;
it does not claim that all board power management is implemented.

The framed reporter optionally invokes a fixed panel-bus helper. It requires
the exact kernel release, Wingray compatible, correct I2C0 DT adapter and a
character device before reading. It reads byte-data at address 0x2c only:
00, 01, 03, 04 and A0–A7. It sends register-selector bytes as part of reads,
never a register-value write, force-access flag, bus scan or EEPROM-program
command. It stops at the first failed read. Settings reflect the bootloader's
handoff state, not necessarily the working Android runtime's settings.

Report shared-regulator state and current clock metadata alongside the existing
fresh storage, GPIO, interrupt and dmesg evidence. No Android filesystem is
mounted and no arbitrary USB command is accepted.

## Checks and acceptance

Full kernel build and compiled DT/config/symbol audit pass. Six actual-script
host tests cover the fixed twelve reads, first-error stop and denial for wrong
release/board/adapter/device. I2C operations and kernel metadata are mocked;
these do not establish actual target transactions. Nine existing transport and
storage regressions pass. Boot image structure was audited.

Image SHA-256:
`81092ac0a891377730749ea7409b8005d91249830334b4b598f1a2adbd6d2de6`.

Fresh preflight must check exact device, AC power, original Android completion,
complete boot/recovery readbacks and original-kernel disk geometry. Test boot
only, collect two fresh checksum-verified reports across close/reopen, then
restore original boot and verify both complete originals. Do not retrieve
reserved RAM in this cycle.

Pass requires USB/storage gates retained, enabled 5 V panel rail and the expected
I2C adapter, all twelve successful fixed reads and chip identity consistent with
the source's LP8550 expectation (`0xfc`). A read error, identity difference or
missing supply remains explicit; no forced access or guessed register write.
This does not validate display timing, backlight control, touch or Android.

## Physical result, 22 October 2026: dependency gate passed

Two fresh reports across serial close/reopen passed nonce, byte count, SHA-256
and completion validation (47,239 and 47,298 bytes). Both retained full disk
capacity and all ten BigPart extents matching the original-kernel reference.
All twelve LP8550 byte-data reads completed without force or register writes.

| Register | Value | Evidence |
| --- | --- | --- |
| 00 | 00 | Brightness register readback |
| 01 | 02 | Bootloader-handoff device control; not rewritten |
| 03 | FC | Expected LP8550 chip identity |
| 04 | 00 | Direct-control readback |
| A0 | 80 | Current-control shadow readback |
| A1–A7 | 67 BF 3F 08 EA 64 2A | Match the original board's initialization values |

The fixed regulator registers as `wingray-panel`, nominal 5,000,000 microvolts;
GPIO 10 / PB2 is owned by it and reports output-high. `num_users=0` reflects
no consumer driver in this profile. The `state` sysfs attribute is absent. In this donor, the fixed driver's
operation table is empty and regulator device registration precedes assignment
of its core-managed enable GPIO. Attribute visibility checks the GPIO pointer
or an `is_enabled` operation when the group is created; that ordering is
consistent with the missing attribute. The on/off inference here uses the
reported GPIO, not an invented `state` value. Neither nominal voltage nor GPIO
output is an electrical voltage measurement.

Clock metadata is available over USB. In the new kernel's handoff state PLL_C
reports 586 MHz and disp1 is parented to it, both with zero software enable
counts. This differs from the sleeping working ROM's captured 598 MHz. It is
not an active pixel-clock measurement or proof that a particular rate is wrong.
Display takeover still needs an explicit parent/divider decision and validation.

The UP CPU-node cap and invalid `fsync_enabled` sysfs-permission warnings are
also present in image 26. They are retained warnings, not evidence that these
I2C reads failed. No I2C transaction error was reported in either capture.

Original boot restoration succeeded. Complete boot and recovery readbacks match
the preserved originals; Android boot completed and its boot ID stayed stable
through verification. No reserved-RAM retrieval, Android filesystem mount,
backlight-value write, display takeover or touch probe was performed. The next
step is a separately reviewed P3 backlight/control implementation followed by
a minimal display-controller test; this result does not validate Android.
