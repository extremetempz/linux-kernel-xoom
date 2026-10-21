# Candidate 22: propagate PHY clock-start errors

Prepared 21 October 2026 after the user returned and requested flashing.

Candidate 21 recorded successful ChipIdea child probe and serial gadget bind,
VBUS present, run/stop set and device mode. These sampled registers do not prove
clock validity, electrical connectivity, interrupt delivery or enumeration.

Patch 0036 (donor commit `42413cbe`) corrects a verified source defect: the
UTMI clock-valid poll could fail while PHY resume still returned success.
Startup now returns that error and uses the existing power-off path to balance
the pad reference and power down a failed PHY. The original startup error is
preserved if cleanup also times out. **No hardware clock timeout has yet been
established, and this is not a confirmed fix for missing enumeration.**
Patch 0037 (commit `6ddda75d`) sets fresh trace cookie `0x584d0016`.

The diagnostic kernel, DT and configuration build pass, as does the measured
boot-image audit. The ramdisk is byte-identical to candidate 21. Offline checks
pass: 24 actual-source clock/error/cleanup cases, 34 compiled bounded USB trace
cases, 8 compiled UDC probe cases, and the decoder regression. Controlled
dependencies are used; these checks do not emulate the Xoom's USB hardware.

Image SHA-256:
`f4354159fd055b2a4a61d86d145e8b2f81a8a48ed212b2dc68571a7f2b85f341`.

## Authorized test

Verify exact device, wall power and both complete preserved images, flash boot
only, observe USB for two minutes, restore original boot, verify complete boot
and recovery readbacks, and retrieve one unchanged 128-byte reserved-RAM trace.
Start the USB watcher before flashing, so the previous late-start observation
gap is avoided. Record expected USB bus visibility separately from tty creation
and report bytes. Recovery, partition layout and Android filesystems are not
modified. Raw evidence remains in ignored private artifacts.

## Physical result and restoration

The boot-only flash and reboot succeeded. The USB watcher started before flashing
and ended with zero report bytes and no expected USB gadget visible on the guest
USB bus. No operator screen change was supplied for this attempt.

The original boot image was restored. Complete boot and recovery readbacks both
match their preserved originals. Exactly one unchanged 128-byte reserved-RAM
snapshot was retrieved after checking the original kernel, boot completion,
reserved mapping exclusion and reader hash. Android remained in the same boot,
with no new fault detected. An initial retrieval invocation stopped on ADB daemon
startup stderr before any partition readback or trace mapping; it performed no
trace read. The later successful invocation made the only mapping attempt.

The record has the expected fresh cookie `0x584d0016` and a valid format-2 header.
This candidate had not previously been tested. It records:

| Observation | Result |
| --- | --- |
| PHY probe and Tegra wrapper | Both returned zero |
| Actual ChipIdea child probe | Returned zero |
| Serial gadget bind | Returned zero |
| Connection state | `0xf`: VBUS active, OTG capable, driver attached, gadget role |
| OTGSC | `0x08200d00`, B-session valid set |
| USBCMD | `0x00010001`, run/stop set |
| USBMODE | `0x0000000a`, device mode |
| Scoped PID 1/direct-child mount | Returned zero |
| Last phase | Init exec succeeded, `0x421` |
| First fatal event / PID 1 user fault | Not recorded |

The patched UTMI resume path now returns a failed clock-valid poll, and the Tegra
wrapper propagates it. Its zero result therefore provides evidence that this
startup poll passed on this attempt. It does not establish continuous clock
health, electrical signal quality or host enumeration. The timeout correction
is useful error handling but did not resolve the observed missing USB gadget.

The register values match candidate 21's connection snapshot. Missing software
VBUS state, a failed child probe and failed serial binding are not supported by
this evidence. No forced VBUS/pull-up or speculative electrical change is
justified. The next discriminating observations are the board's USB data-switch
GPIO state, host reset/setup activity and controller interrupt delivery. These
were not captured by the current 128-byte schema; their absence is not a result.

Linux 4.4 Android startup and continuous diagnostic userspace health remain
unverified. No further hardware test, flash or background watcher was started.
