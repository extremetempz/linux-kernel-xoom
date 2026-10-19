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

## Physical boot attempt, 2026-10-18

Bootloader 1050 identifies `xoom-wifi` and reports `unlocked: yes`. It accepts
image downloads but rejects `fastboot boot` with remote error 0x8. The user
confirmed the on-screen message: “Boot command is not allowed on consumer
devices.” No kernel execution occurred through the RAM boot command. A matching
historical report is at https://groups.google.com/g/android-kernel/c/tawg8KHJSQA .

The user subsequently authorized writing a diagnostic image to boot and restoring
the original afterward. The diagnostic image uses the measured v0 image layout,
a BusyBox-based initramfs with dependency closure copied from the tablet, and
no Android partition mounts. Its SHA256 is
`c7245a700685f175b390a883316c127a911611a136ee4755746211ed3f4df493`.

Fastboot reported successful boot-partition writing and reboot. The screen stayed
at the Motorola logo, and no diagnostic USB ACM gadget appeared within 45 seconds.
This is a failed bring-up test: there is no evidence yet of how far the kernel
executed. Display, touch, Wi-Fi and power drivers remain unvalidated. Do not infer
a specific failing driver from the boot logo. Restoration is the immediate next
step; record its verification separately.

The diagnostic image and its proprietary runtime remain local under ignored
`artifacts/`. Only the construction scripts belong in GitHub. `0003` enables
kernel debugfs for diagnostics; it does not fix the boot failure.

### Restoration verified

Fastboot successfully wrote the complete original boot backup and rebooted.
ADB confirmed Android 4.4.4, kernel `2.6.39.4-ElementalX-Xoom-2.1+` and
`sys.boot_completed=1`. A fresh read of the entire 8 MiB boot partition matched
the original backup byte for byte. Recovery and partition layout were not
written during the test. The retained `/proc/last_kmsg` contains Linux 2.6.39
output, not a diagnostic Linux 4.4 log. That test therefore does not locate the
new kernel's failure.

### Candidate 10 trace and restoration

Candidate 10 was subsequently written to the boot partition for a diagnostic
attempt. Fastboot reappeared before the intended two-minute observation ended,
and available evidence cannot tell whether this was a button-driven handoff or
an automatic return. No USB ACM serial device or ADB device was visible while
the candidate was active.

After restoring the original boot image, full boot and recovery readbacks
matched their preserved originals byte for byte. Android 4.4.4 reached
`sys.boot_completed=1`. A single bounded read retrieved a valid trace with
cookie `0x584d000a`; its last phase was `0x9002ebff`, a sampled page-metadata
PFN inside `memmap_init_zone`. The zone-loop return marker, enclosing
`memmap_init` return marker, and first-fatal PC were absent. This places the
last observed progress late in memory-zone initialization but does not
establish a fault or a permanent hang. See the [candidate 10 test record](trace-boot-attempt-10.md).

Subsequent diagnostic iterations are limited to the boot partition and restore
the verified original afterward. Recovery, partition layout and Android data
remain untouched. The working Android ROM was verified after candidate 11;
the new kernel has not reached Android.

### Candidate 11 repeatability check

Candidate 11 used the same sparse page-progress instrumentation as candidate
10 with a fresh cookie (`0x584d000b`). It was built and statically checked,
then written to the boot partition only. The tablet stayed at the Motorola
logo; after about three minutes it enumerated as Google Fastboot. No diagnostic
USB serial or ADB device appeared. The available observation cannot establish
whether the bootloader return was automatic or button-driven.

After restoring the original boot image, Android 4.4.4 reached
`sys.boot_completed=1`; complete boot and recovery reads again matched their
preserved originals byte for byte. One bounded trace read returned the expected
cookie and the same last sampled phase as candidate 10, `0x9002ebff` (PFN
`0x2ebff`). The trace still had no `memmap_init_zone` return, enclosing
`memmap_init` return, or first-fatal PC. The reader reported no transport
stderr, the Android boot ID stayed unchanged, and dmesg did not change during
retrieval. This makes the last sparse checkpoint repeatable across two builds;
it does not identify a fault or an exact failing PFN. See the [candidate 11
record](trace-boot-attempt-11.md).

### Candidate 12 preparation

Candidate 12 is built but has not been written to the device. It records the
active `memmap_init_zone()` PFN bounds and adds four possible progress stores
across 64 PFNs around `0x2ebff`, while retaining the 512-PFN global sampling
interval and leaving page initialization unchanged. The compiled allocator
harness and existing boot-entry, mapping, fatal-path, trace-reader, and
BigPart checks passed. The trace-disabled early profile also builds. See the
[candidate 12 design and build record](trace-node-map-candidate.md). A later
boot-partition test must continue to restore and verify the original boot and
recovery images before interpreting the trace.
