# Candidate 23: USB switch GPIO initialization dependency

Prepared 21 October 2026 in response to the request to review the logs, find the
failure, fix it, and consider the bigger picture. This continues the existing
4.4.147 port and the authorized boot-only diagnostic/restoration workflow.

## What is already established

Candidate 22's fresh record confirms execution reached the diagnostic init and
a PID 1/direct-child mount returned zero. PHY startup, actual ChipIdea child
probe and serial gadget binding returned zero. VBUS/B-session-valid and device
mode/run bits were set at sampled checkpoints; no fatal event was recorded.
The guest saw no expected USB device or serial report during observation.

This does not establish a kernel hang at the Motorola logo. The current image
starts a RAM diagnostic, with display and Android startup deliberately excluded.
The immediate problem is missing USB observability; Android bring-up still
requires the remaining board/peripheral and userspace integration.

## Verified source defect

The working 2.6.39 board code explicitly requests PV4 `usb_data_en` and drives it
high to connect the external USB data switch. It requests PC5 `usb_forceon_n`
and drives it high as well. The new DT describes the same levels using GPIO
hogs with distinct expected owner labels.

The donor's GPIO driver registers at `postcore_initcall`, before the Tegra20
pinctrl driver's normal device initcall. The inherited Tegra20 GPIO node has its
`gpio-ranges` property commented out. GPIO registration therefore proceeds to
the one-shot hog scan before the pin provider's legacy range exists:

1. `of_gpiochip_add_pin_range()` finds no DT range and returns zero.
2. `of_gpiochip_scan_gpios()` attempts each hog.
3. Tegra's GPIO request calls `pinctrl_request_gpio()`, which returns
   `-EPROBE_DEFER` while no provider/range exists.
4. A failed hog is logged and skipped; the scan and GPIO-controller probe still
   return success. Later pinctrl registration does not retry the skipped hogs.

This is a source-level initialization defect. It permits all USB driver probes
and gadget binding to succeed without establishing the board's USB data path.
The old trace did not measure these GPIOs, so **the physical effect on builds
21/22, and whether this explains missing enumeration, remain unproven**. Inherited
firmware GPIO state must not be assumed either enabled or disabled.

## Correction and instrumentation

Patch 0038, donor commit `5e6035ff`, adds the GPIO-to-pinctrl range dependency to
Wingray only: `<&pinmux 0 0 224>`. The GPIO probe can then defer before scanning
hogs, and retry after provider registration. Tegra's legacy fallback detection
now recognizes Tegra20 as well as Tegra30 GPIO nodes, avoiding a duplicate
legacy range when Tegra20 declares the DT range. It does not change output
levels or add speculative electrical settings.

Patch 0039, commit `6882eb27`, adds a read-only snapshot after successful GPIO
registration on a traced Wingray. For PV4 and PC5 it records GPIO CNF, output
enable, output latch, and whether the request owner matches the expected DT
label. `GPI1` reuses two completed early-init marker words (0x48/0x4c) inside the
unchanged 128-byte record. USB/fault fields remain separate. The helper checks
readiness/header/cookie/first-fatal state, masks IRQs briefly on the UP diagnostic,
and does not use freed init code. No GPIO writes or extra physical memory reads
are introduced by the snapshot.

Expected state is `0xff`: both lines in GPIO mode, output-enabled, latched high,
and requested under the expected label. This is a register/ownership snapshot,
not a measurement of pin voltage, tristate, signal quality or USB traffic.
Patch 0040, commit `df1e453c`, sets fresh candidate cookie `0x584d0017`.

## Offline evidence

The actual OF add/range/scan, GPIO hog, pinctrl request and Tegra GPIO request
functions are compiled in a dependency-controlled host fixture. It reproduces
the historical order (successful controller registration, two failed hogs,
no later retry) and verifies the corrected defer-before-scan/retry path. Provider-
first DT/legacy ranges on Tegra20/Tegra30 and absent-provider detection are also
checked. DT/provider/descriptor/configuration dependencies are controlled; this
does not emulate a complete boot or prove previous hardware state.

The actual read-only GPIO snapshot function passes all 256 combinations of its
eight register/owner flags, plus non-Wingray exclusion. Twenty-two actual compiled
trace-helper cases check bounded writes, header/fatal guards, IRQ restoration,
USB/user-fault preservation and inaccessible init memory. Thirty-four compiled
USB trace cases and the decoder regression also pass.

The diagnostic kernel/DT/config build and boot-image layout audit pass. The
compiled DT is checked for the real provider phandle, base and count. The RAM
runtime is byte-identical to build 22. Image SHA-256:
`8da7bcd10e0650d0288ffc6ff32adca6a9327633c73d0240be3e9b7057419282`.

## Authorized physical validation

Before any write, verify exact device, wall power and complete original boot
and recovery readbacks. Flash boot only, observe USB from before launch for two
minutes, restore original boot, verify both originals, then retrieve one unchanged
128-byte reserved-RAM trace. Preserve raw evidence privately. Recovery, partition
layout and Android filesystems stay outside this test's write scope.

A successful GPIO state without enumeration would leave reset/setup/IRQ handling,
pinmux/electrical state and host passthrough as separate unresolved branches.
Do not declare the enumeration cause fixed from a build or register snapshot.

## Physical result

The boot-only flash/reboot succeeded. The watcher was started before launch.
At approximately 25 seconds after launch, the guest observed `0525:a4a7` and
created `ttyACM0`. Sysfs reports speed `480`, configuration value `2`, two
interfaces and authorization enabled. This is the first observed gadget
enumeration in these tests. Host configuration and CDC ACM creation establish
that the USB control path progressed beyond the earlier register snapshots.

Initial report capture stopped on a host `PermissionError`: the temporary node
was owned by root/dialout, while the account had no dialout access. The operator
granted a per-user ACL on that node using sudo in their own terminal; no password
was shared and no account-group or persistent host policy change was made.

The subsequent capture received **34,370 bytes**, with both
`XOOM_DIAGNOSTIC_BEGIN` and `XOOM_DIAGNOSTIC_END` markers. The application sent
no command bytes during that capture. The report includes Linux
`4.4.147-wingray-diagnostic`, successful `g_serial` registration and these actual
kernel messages:

- At 0.008574 s, the GPIO controller's initial registration failed while its
  new range dependency deferred it. No failed-hog messages are present.
- Pinctrl initialization completed at 0.072422 s.
- At 0.541098 s, GPIO 172 `wingray-usb-data-enable` was hogged as output/high.
- At 0.541936 s, GPIO 21 `wingray-usb-forceon-n` was hogged as output/high.

This is consistent with the intended defer-before-scan, register-provider, then
retry sequence. The framed report contains some interleaved/malformed text;
marker completion is not a checksum or proof that every byte is intact.

A separate bounded follow-up sent only a fixed read-only command containing
`cat /proc/partitions` and `dmesg`, with printf delimiters. It received malformed
command echo and shell syntax errors, without either live-response delimiter.
**It is not a valid fresh storage/log result.** Serial line-discipline or
bidirectional transport handling remains unresolved; no cause is established.
Do not claim a reliable interactive shell or successful execution of those reads.

## Restoration and one bounded trace

The original boot image was restored and recovery was not written. Complete
readbacks of both partitions match their preserved originals. The working
Android ROM is running again. The temporary serial node disappeared during the
USB mode change, so its per-node ACL is not a persistent account policy change.

One unchanged 128-byte reserved-RAM trace has the expected fresh cookie
`0x584d0017` and a valid header. The first retrieval invocation stopped at absent
ADB USB before any readback or mapping; after reconnection, the only mapping
attempt completed. Same Android boot, boot completion and no new fault after
retrieval were checked.

The GPIO snapshot is **`0xff`**: PV4 and PC5 were each in GPIO mode,
output-enabled, latched high, and requested under the expected board label.
Actual USB child probe and gadget bind returned zero; VBUS/B-session-valid,
device mode and run/stop were set. Init exec and a scoped mount succeeded;
no first fatal event or PID 1 user fault was recorded.

## Verdict and limits

The GPIO initialization dependency defect was reproduced in actual source flow
and corrected. Candidate 23 now establishes the intended USB-switch ownership
and register state, enumerates at high speed and transmits a framed boot report.
This validates the corrected USB setup on the device and is strong evidence
that the change resolved the observed enumeration blocker. **Previous attempts'
GPIO electrical states were not captured, and no controlled physical reversion
was performed; do not assert that every earlier failure had this cause.**

Linux 4.4 has booted the RAM diagnostic and delivered its report over USB. It has
not booted Android or validated display, touch, Wi-Fi or power management.
The report records a CPU-map warning (two DT CPUs with the UP diagnostic limited
to one) and a donor sysfs warning (`fsync_enabled` permissions 0755). Neither
stopped this boot. Its SDHCI controller was registered, but the initial report
has no eMMC block-device result; it was generated very early in asynchronous
card discovery. The failed live read means storage status remains unverified,
not proven broken or working.

Next work should make report requests/serial handling reliable, obtain a fresh
read-only eMMC/BigPart result, then validate the required board peripherals and
Android integration. No further flash, device test or background watcher was
started after restoration. Raw reports, identifiers and images remain private.
