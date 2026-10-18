# Wingray hardware validation

## Evidence collected on 2026-10-18

Read-only diagnostics were collected from the actual MZ604, running Android
4.4.4 and Linux 2.6.39.4-ElementalX-Xoom-2.1+. No flash or repartition operation
was performed. Raw captures and boot/recovery backups remain in the ignored
`artifacts/hardware-private` directory; they must not be published.

The tablet is a P3 board with an AUO 1280x800 display. Its touchscreen reports
firmware 0x10FF. I2C enumeration confirms LP8550 backlight at 0x2c, maXTouch at
0x5b, and MAX8649 CPU regulator at 0x60 on the DVC controller. Motorola's
board sources and the live pinmux capture supply the GPIO configuration.

The GPT header and entries passed CRC checks. The bootloader supplies GPT LBA
62513151, rather than the physical last sector. Live partitions agree with the
BigPart transformation: system starts at 118784 with 2097152 sectors; cache at
2215936 with 1048576 sectors; userdata at 3264512. The original GPT is not
rewritten. The new parser's fallback is restricted to the Wingray eMMC.

The existing Android boot header loads its kernel at 0x10008000, ramdisk at
0x11000000 and tags at 0x10000100, with 2048-byte pages. This puts zImage outside
the automatic decompressor's first-128MiB assumption. The Wingray build now
explicitly decompresses to physical 0x8000, matching Motorola's original kernel.

## Implementation and remaining validation

| Area | Source implementation | New-kernel hardware result |
| --- | --- | --- |
| Power rails | CPCAP MFD/regulator backport, Wingray regulator modes, MAX8649 DT support | Not boot tested |
| Restart/power off | CPCAP reboot flags and dedicated board GPIOs | Not boot tested |
| Display | AUO timing, panel supply, Tegra DRM, LP8550 backlight | Not boot tested |
| Touch | P3 PV2 interrupt, active-low reset/wake, existing controller configuration retained | Not boot tested |
| Wi-Fi | BCM4329 SDIO, PU4 power/PU2 reset, PU5 host wake, board delays/tap | Not boot tested; firmware/NVRAM integration pending |
| Storage | eMMC, external SD, scoped relocated-GPT and BigPart support | Live old-kernel geometry verified; new driver untested |
| Pinmux | Live working P3 mux/pull/tristate mapped into DT | Not boot tested |
| Suspend/DVFS | Deliberately disabled during bring-up | Not implemented/validated |
| Battery/charging | CPCAP core is a prerequisite | Charger, fuel gauge and thermal integration pending |
| Audio/Bluetooth/cameras/sensors/HDMI | Inventory captured; original drivers available for reference | Porting pending |

Wi-Fi firmware exists as `/system/vendor/firmware/fw_bcmdhd.bin` on the working
ROM. Mainline brcmfmac expects a different firmware filename and board NVRAM;
chip identity, firmware compatibility and MAC handling require runtime checks.
Do not distribute the device's NVRAM or assume that a firmware filename proves
compatibility.

## Next hardware test

First produce a diagnostic RAM boot image with a read-only environment and
serial-over-USB logging. Verify the original boot/recovery backups and image
addresses, then use a temporary boot only if the bootloader supports it. Do not
flash the candidate, mount Android storage writable, or change BigPart. Confirm
boot logs, CPCAP identity, rail state, display/backlight, touch input and SDIO
probe before enabling suspend or attempting a ROM. Cross-compilation alone is
not evidence of working hardware.
