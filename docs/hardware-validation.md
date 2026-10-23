> **23 October 2026 — image32:** Android Welcome responds to real touch. Three fresh USB reports retain Android boot completion, full eMMC/all ten BigPart extents and read-only storage. Evdev verifies presses, movement, releases and two active contacts. Complete original boot/recovery match after restoration. A startup IRQ burst has a separate built, unflashed correction; full calibration/suspend and lockscreen remain unverified. See [result](trace-boot-attempt-32.md).

> **22 October 2026 — image31:** First completed Android 4.4.4 boot under Linux 4.4.147. Two fresh verified reports show both boot-completion flags set and SystemUI running; logs and operator confirm the Welcome screen. USB/full capacity/all ten BigPart extents remain correct under the read-only system/RAM-data policy. Both complete original images match after restoration. Touch is disabled; a lockscreen and full peripheral support remain unverified. See [result](trace-boot-attempt-31.md) and [isolated touch plan](touch-next-stage.md).

> **22 October 2026 — image29:** First operator-confirmed visible RGB pattern under Linux4.4. Two fresh reports verify 1280×800×32 fb0, connected/enabled LVDS, capped P3 backlight control, advancing DC interrupts, retained USB/full capacity/all ten BigPart extents. Full original boot/recovery readbacks match after restoration and original Android runs. Android under Linux4.4 and touch were untested at this stage. See [result](trace-boot-attempt-29.md).

> **22 October 2026:** Image 27 retains USB/full-capacity/all-ten-BigPart matching and completes twelve guarded LP8550 reads twice (identity FC). The shared panel regulator claims PB2 output-high; the 5 V sysfs value is nominal, not an electrical measurement. Both complete original images are verified after restoration. Display takeover/backlight programming and touch remain pending. See [image 27](trace-boot-attempt-27.md).

> **21 October 2026:** Linux 4.4 boots RAM diagnostic userspace and USB is hardware-tested. Image 26 passed two fresh checksummed reports with the original kernel's full eMMC capacity and all ten BigPart extents. Original boot was restored and both complete original images verified. See [image 26](trace-boot-attempt-26.md). Display/input and power management remain unverified; this is not an Android boot.

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
| Shared panel/I2C | PB2 fixed rail and I2C1 pin/adapter path | Image 27: claimed output-high and twelve fixed register reads pass twice; no electrical voltage or display validation |
| Power rails | CPCAP MFD/regulator backport, Wingray regulator modes, MAX8649 DT support | Not boot tested |
| Restart/power off | CPCAP reboot flags and dedicated board GPIOs | Not boot tested |
| Display | AUO timing, panel supply, Tegra DRM, LP8550 backlight | Image 29 RGB; images 31/32 Android Welcome; accelerated GPU unvalidated |
| Touch | Isolated P3 PV2 interrupt, active-low reset/wake, factory T9 retained | Image 32 real UI response, presses/movement/releases and two active contacts; startup IRQ burst recorded separately |
| Wi-Fi | BCM4329 SDIO, PU4 power/PU2 reset, PU5 host wake, board delays/tap | Not boot tested; firmware/NVRAM integration pending |
| Storage | eMMC, external SD, scoped relocated-GPT and BigPart support | Image 26: eMMC full capacity and all ten BigPart extents match twice; external SD, filesystem and stress checks pending |
| Pinmux | Live working P3 mux/pull/tristate mapped into isolated DT | Display/USB/eMMC and touch pin groups physically exercised; broad peripheral tree unvalidated |
| Suspend/DVFS | Deliberately disabled during bring-up | Not implemented/validated |
| Battery/charging | CPCAP core is a prerequisite | Charger, fuel gauge and thermal integration pending |
| Audio/Bluetooth/cameras/sensors/HDMI | Inventory captured; original drivers available for reference | Porting pending |

Wi-Fi firmware exists as `/system/vendor/firmware/fw_bcmdhd.bin` on the working
ROM. Mainline brcmfmac expects a different firmware filename and board NVRAM;
chip identity, firmware compatibility and MAC handling require runtime checks.
Do not distribute the device's NVRAM or assume that a firmware filename proves
compatibility.

## Next hardware gate

Preserve image 32 as the working Android/touch control. Patch 0059 closes a
startup touch IRQ request race and has passed host tests/full kernel compilation;
its removal of the physical burst still needs a boot-only test/restore cycle.
Keep read-only eMMC, RAM-data/cache and the original image checks. Confirm edge
alignment, two-contact release and stable IRQ behavior before suspend or broader
power changes. The Decatf reuse review will stage SMP, PL310, voltage/EMC and
legacy graphics separately; no Samsung board tables are authorized by the shared
SoC alone. Cross-compilation alone is not hardware validation.

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
[candidate 12 design and build record](trace-boot-attempt-12-prepared.md). A later
boot-partition test must continue to restore and verify the original boot and
recovery images before interpreting the trace.

## Candidate 13 physical test — 20 October 2026

The boot-only diagnostic reached sampled PFN `0x2ec2f` in early page metadata
initialization, with valid fresh cookie and active-zone/descriptor metadata.
It still has no memmap return, initcall or Android boot. Original boot and
recovery readbacks match after restoration; Android is running. See
[candidate 13](trace-boot-attempt-13.md) for the verified record, offline test
limits and an unconfirmed descriptor-address correlation with the video
reservation boundary. No peripheral runtime validation is claimed.

## Candidate 14 — memory failure passed

The lowmem-limit correction changed the active zone end from PFN `0x30000`
to `0x2e800`. A fresh valid trace records architecture setup returning and
reaching the early initcall, followed by a later panic with no captured text.
Original boot/recovery readbacks match after restoration; Android is running.
See [candidate 14](trace-boot-attempt-14.md). This advances kernel startup;
it does not validate Android or peripheral operation.

## Candidates 15 and 16 — init execution reached

Candidate 15 completed basic setup but a new diagnostic hook called freed
flat-DT init code; the captured PC was reproduced offline. Candidate 16's
readiness-guard correction reached `init_exec_succeeded`, followed by a panic
with truncated prefix `Attempted to`. It has not booted Android. Original
boot/recovery were restored and verified after both tests. See
[candidate 15](trace-boot-attempt-15.md) and
[candidate 16](trace-boot-attempt-16.md). USB PHY inclusion was separately
found defective in the donor build wiring; candidate 17 corrects it and
adds explicit PID 1 exit-status capture.

## Candidate 17 — init death identified

The fresh bounded trace records init exec succeeding, then PID 1 dying with
SIGSEGV (wait status `0xb`, no core flag) before panic. No expected USB serial
gadget/report was observed in this VMware guest. The real USB PHY is now
linked in diagnostic and full peripheral builds; its runtime probing remains
unverified. Both original images match full readbacks after restoration.
The exact prepared BusyBox/linker/library closure passes a separate isolated
root check under the working kernel, without mounting any filesystem.
See [candidate 17](trace-boot-attempt-17.md). Android under 4.4 and peripheral
runtime operation remain unverified.

## Candidate 18 — userspace fault location captured

A valid fresh trace records PID 1's first ARM userspace page fault: Thumb PC
`0xb6f12996`, unmapped address `0x90`, FSR `0x5`, followed by SIGSEGV/init-death
panic. The executable/library mapping is not yet known. Both complete
original images match after restoration; Android remains running after the
single bounded trace read. No USB serial report reached this guest. See
[candidate 18](trace-boot-attempt-18.md). This narrows early userspace failure;
it is not an Android boot or peripheral validation result.

## Candidate 19 — previous diagnostic fault absent

The static-runtime candidate records init exec with no first-fatal, user-fault
or init-exit record. Its runtime passes independent raw-exec controls under
empty and kernel-like environments on the working kernel. USB is still not
observed, and the trace has no post-exec activity checkpoint, so continuous
userspace operation and peripherals remain unverified. Both full original
images match after restoration; Android remains running after one bounded
trace read. See [candidate 19](trace-boot-attempt-19.md) for limitations and
the staged post-exec/USB/eMMC/Android validation plan.

## Candidate 20 — post-exec activity and successful probe returns

The valid fresh trace records a successful mount syscall from PID 1 or a
direct child, and zero return status from both USB PHY and UDC probes. No
fatal event is recorded. This confirms post-exec activity, but not completion
of the diagnostic script or USB enumeration. Neither guest nor operator
observed the expected gadget. Original boot/recovery readbacks match after
restoration, and Android remains running after the one bounded trace read.
See [candidate 20](trace-boot-attempt-20.md). Next observation points are
gadget binding, the unchecked PHY-resume result, VBUS and pull-up sequencing.

## Candidate 22 USB result, 21 October 2026

The fresh candidate-22 trace confirms actual USB child probe and serial-gadget
binding returned zero; VBUS, B-session-valid, device mode and run/stop were set
at sampled checkpoints. The corrected PHY startup returned zero, providing
evidence its clock-valid poll passed. No expected gadget/report was observed
by a guest watcher started before flashing. The physical enumeration cause is
still unresolved: board data-path GPIO state, reset/setup activity and IRQ
delivery require further observation. No fatal event was recorded, and a scoped
userspace mount succeeded. Linux 4.4 Android startup remains unverified. Original
boot and recovery full readbacks match after restoration; Android is running.
See [candidate 22](trace-boot-attempt-22.md) for evidence and limits.

## Candidate 23 USB milestone, 21 October 2026

The corrected GPIO-to-pinctrl dependency permits the one-shot USB-switch GPIO
hogs to run after pinctrl registration. The real kernel log records both hogs
output-high and the bounded trace records `0xff` for expected ownership plus
CNF/OE/OUT states. The guest observed high-speed USB configuration and ttyACM0;
a framed 34,370-byte report identifies Linux 4.4.147 diagnostic userspace.
A fresh interactive read failed with malformed input and is not evidence of
storage status. eMMC/BigPart, reliable bidirectional console, Android startup
and remaining peripherals are still unverified. Both original images match
complete readbacks after restoration, and Android is running. See
[candidate 23](trace-boot-attempt-23.md) for verified facts and causal limits.
