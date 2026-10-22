> **22 October 2026 update:** Image29 passed the first visible RGB scanout and P3 backlight test with retained USB/storage. Both originals are verified after restoration. The active next gate is Android ABI/init/graphics integration toward a real lockscreen; unrelated peripherals are deferred. See [image29](trace-boot-attempt-29.md) and [Android gates](android-boot-gates.md). The storage plan below is retained as historical context.

# Next porting stage: trustworthy live storage evidence

Decision, 21 October 2026: retain candidate 23's hardware-tested Linux 4.4.147
kernel and correct the RAM diagnostic transport before changing eMMC drivers.
This continues the existing port, reservations, BigPart view and backups.

## Evidence and uncertainty

The new kernel reaches diagnostic userspace, configures both USB-switch GPIOs,
enumerates at high speed and transmits a report. Candidate 23's report was cached
at approximately 0.55 seconds, while MMC discovery is asynchronous. It showed an
SDHCI controller but no block disk. A later interactive read had malformed input
and no valid response delimiters. Neither establishes whether eMMC ultimately
appeared. TTY echo, framing, startup timing and bidirectional transport remain
plausible causes of the malformed session; none is established as the cause.

A speculative MMC timing, voltage or regulator change would mix an unverified
storage diagnosis with an unresolved observation path. First make observations
fresh and integrity-checked, then choose a source correction from the result.

## Stage 24: fresh read-only reporter

Image 24 reuses candidate 23's exact kernel/DT/config bytes. Its trace cookie
therefore remains `0x584d0017`; there is no claim of a new kernel revision or a
new uniquely identified RAM trace. This cycle does not retrieve reserved RAM.
Fresh reports instead correlate to a random host request nonce and contain
current uptime, current metadata and current dmesg.

The RAM init mounts virtual filesystems only. The device disables terminal echo
and output translation before accepting requests, sends no unsolicited report,
and accepts only `PING <nonce>` and `REPORT <nonce>`. It never evaluates USB
input as shell code. The host configures raw mode, completes a retryable
nonce-correlated readiness handshake, and requests a report. The response carries
a byte count, SHA-256, base64 payload and matching end marker. The host rejects
incomplete, stale, oversized or corrupt responses instead of treating markers
alone as evidence of intact logs.

Each report waits at most 20 seconds for all ten eMMC partitions, then explicitly
reports present/missing disk and partitions, sysfs start/size, mounts, MMC devices,
interrupts, GPIO state and dmesg. No Android filesystem is mounted, no raw block
write or configuration command is exposed, and output files live in RAM tmpfs.
The old interactive mode remains available only for explicit reproduction.

Acceptance criteria:

1. Repeated fresh requests after port close/reopen complete with exact nonce,
   length, checksum and payload markers. Local PTY tests are necessary but do
   not validate the target USB hardware or the exact ARM BusyBox shell version.
2. Mount evidence contains virtual filesystems only.
3. New-kernel disk capacity and all ten partition start/size pairs match a fresh
   reference read from the restored original Android kernel before the test.
   Compare the **live BigPart view**, not the legacy raw GPT entries; their
   system/cache/userdata extents intentionally differ.
4. Missing disk/partitions, command timeouts or geometry mismatches remain explicit
   failures/unknowns. Do not mount storage or compensate by repartitioning.
5. Restore original boot and compare complete boot/recovery readbacks regardless
   of the diagnostic outcome. Preserve raw reports privately. No RAM mapping is
   needed when report integrity can be checked through USB.

## Next branches

- If eMMC and geometry match, the storage-discovery gate is passed. Next validate
  the minimum board power/display/backlight/touch profile with USB logs retained.
- If eMMC is absent after the bounded wait, use fresh MMC command/error/IRQ and
  controller evidence to distinguish pinmux, clock/reset, power, tap timing and
  driver quirks. Make one supported correction and test it separately.
- If the report fails integrity or readiness, fix the observation path without
  changing storage drivers or declaring an eMMC failure.

Android needs a separate integration stage: kernel services/ABI, initramfs/fstab
paths, compatible graphics interfaces/userspace, then framework/UI startup.
Existing legacy NVIDIA ioctl expectations and the current DRM path still need a
compatibility decision. USB or storage success does not prove an Android boot.
Suspend, CPU frequency control and broad peripheral enabling remain outside this
minimal test. Estimates for Android completion cannot be justified yet.

## Stage 24 outcome and stage 25 correction

Both fresh framed reports passed integrity checks. eMMC was present and all ten
BigPart partition extents matched, but whole-disk capacity was 4 MiB short.
The gate remains closed on that discrepancy. See the image-24 result.

Image 25 preserves raw sector count only for nonremovable Wingray eMMC on the
controller marked `motorola,xoom-bigpart`. Other donor hosts retain their prior
policy. A separate commit changes the trace cookie. Keep the same diagnostic
service, device tree, clocks and power settings. Test that capacity becomes
62,521,344 sectors while all ten extents still match; restore originals and
verify complete readbacks. Do not mount Android filesystems in this cycle.

If that passes, prepare the display/panel/backlight/touch dependency review and
minimum USB-observable board profile. This is still separate from Android
services and graphics ABI integration.

## Stage 25 outcome and stage 26 parser correction

Image 25 confirms the full disk capacity on hardware, but discovers no
partitions. A compiled actual-dispatcher/handler test reproduces the broad
`gpt` setup handler consuming `gpt_sector=` when it appears first in the setup
table, as it does in image 25. The formerly reduced apparent end masked this.
Image 26 adds exact-token parsing and logs the scoped relocated-GPT attempt.
It retains the capacity correction; the same full-capacity/all-extents gate
must pass before proceeding. No filesystem mount or on-disk GPT repair.

## Stage 26 passed: next boundary is board display/input

Two fresh integrity-verified reports confirm the corrected relocated-GPT path,
62,521,344 sectors and all ten matching BigPart extents. Original boot/recovery
are fully verified after restoration; original Android is running. This passes
the storage-discovery/geometry gate, not filesystem integrity or I/O stress.

The next profile must retain the tested USB/MMC setup and memory reservations:

1. Review the P3/AUO panel, CPCAP supplies, backlight and I2C dependencies against
   working-board sources. Check their probe and sequencing requirements before
   enabling them. Capture regulator/clock/provider errors over the fixed USB
   reporter, without exposing arbitrary hardware-write commands.
2. Enable only required board power and display dependencies, leaving Wi-Fi,
   suspend, DVFS and unrelated peripherals disabled. Build/audit separately from
   adding Android kernel services. Validate driver binding and supply state,
   then an observable panel/backlight result; use measured logs, not a retained
   Motorola logo, to judge new display execution.
3. Add touch only after its rail, reset polarity and interrupt dependencies have
   been reviewed. Test input events with a bounded diagnostic; a bound I2C device
   alone does not validate coordinates or interrupts.
4. Resolve the legacy NVIDIA graphics/userspace interface decision before trying
   installed Android init. The minimal DRM path is not proof that the old binary
   EGL/compositor stack is compatible. Then prepare distinct kernel-service/ABI
   and initramfs-path configurations for the chosen Android release.

These are future stages, not completed code or hardware validation. Each test
keeps boot-only restoration, complete original checks and private raw evidence.
No ROM install, partition write or recovery write is authorized by this plan.

## Stage 27: shared panel supply and bus before display takeover

The P3 board source uses PB2 as the shared panel/I2C supply; the older PD0 gate
is not the P3 LP8550 path. Its P3 backlight driver uses control 0x03 and scaled
A0 LED-current updates, unlike the broad profile's generic brightness-register
path. Do not enable the broad peripheral profile to bypass that discrepancy.

Image 27 retains image26 USB/MMC and adds only the fixed panel supply, two I2C1
mux groups and adapter/character driver. Read twelve fixed LP8550 registers
without force, scanning, value writes or programming. Check regulator software
state (nominal voltage, not an electrical measurement), fresh storage geometry,
USB report integrity and current clocks. Settings reflect the bootloader handoff.
See [image 27](trace-boot-attempt-27.md). Display controller and backlight control
remain disabled for this dependency test; no Android mount or reserved-RAM read.

If this passes, implement and test the P3-specific brightness/current behavior
before display takeover. Choose the RGB parent/divider from source and active
clock measurements; the existing PLL_P default must not be assumed to reproduce
the old PLL_C path. Retain hardware-observable evidence and the restoration gate.

## Stage 27 outcome, 22 October 2026

The isolated panel-supply/I2C test passed twice with intact framed USB and
storage geometry. All twelve fixed LP8550 reads completed, chip identity was
FC, and PB2 was claimed output-high by `wingray-panel`. Nominal regulator voltage
is 5 V; no electrical measurement was made. Original boot/recovery are fully
verified after restoration and original Android is running.

The control byte at handoff was 02 and A0 was 80; A1–A7 match the original board
settings. The new-kernel clock report records PLL_C/disp1 at 586 MHz with zero
enable counts, while the sleeping old-ROM capture reported 598 MHz. These are
software handoff states, not measured active pixel clocks. Retain these facts
when implementing the P3 backlight driver and minimal display takeover; avoid
assuming that the retained Motorola logo validates scanout. No display, touch
or Android startup is claimed by the successful bus test.
