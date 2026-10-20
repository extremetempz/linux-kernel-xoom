# Candidate 19: standalone static diagnostic runtime

Tested 20 October 2026. The fresh physical trace reaches init exec with no
recorded user fault, init exit or fatal event. No USB report was observed.
Original boot/recovery are restored and verified; Android is running.

## Targeted correction

Candidate 18 reaches init exec, captures a userspace fault accessing `0x90`,
then records PID 1 SIGSEGV. Subsequent controls on the working kernel isolate
a diagnostic-runtime dependency on inherited `ANDROID_PROPERTY_WORKSPACE`.
See [candidate 18](trace-boot-attempt-18.md). This did not establish that the
same PC faulted in both cases, but it exposes an independent initramfs defect.

The diagnostic builder now accepts a static ARM BusyBox, packaging only
`bin/busybox` instead of the copied Android linker/library closure. Historical
Android mode remains available for reproduction. The init/report scripts
and hardware settings are retained. Only the kernel's fresh trace cookie
changes (`0x584d0013`, patch 0030); no new driver fix is bundled into this test.

The runtime is the [official BusyBox 1.31.0 ARMv5 binary](https://busybox.net/downloads/binaries/1.31.0-defconfig-multiarch-musl/),
pinned by `scripts/fetch-diagnostic-runtime.py`. SHA-256:
`69bbb65ccd70481ec2df19b8770b2e979aeb75dddf08d2fc5b0230f892989c40`.
It has no ELF interpreter or shared-library dependency. ELF attributes show
ARMv5T, VFPv2 and no NEON attribute; the exact binary executes successfully
on this Xoom. The published source is [BusyBox 1.31.0](https://busybox.net/downloads/busybox-1.31.0.tar.bz2).
This is a diagnostic userspace, not a replacement Android ROM.

## Validation and recovery

Independent static raw-exec launchers start the exact replacement in an
isolated temporary root under inherited, empty and kernel-like environments.
All three print the control marker and exit zero on the working kernel.
Required init/report applets are present. No filesystems are mounted, Android's
boot ID stays unchanged and each temporary root is removed afterward.
`tests/runtime-exec-probe.S` is the raw-exec source (modes 0=inherited,
1=empty, 2=HOME/TERM, 3=explicit variables supplied as launcher arguments).

The new kernel/DT image, resolved profile and Android boot-image layout pass
validation. Compiled first-user-fault and init-exit helper checks pass, and
the clean donor checkout contains the complete patch series. Preflight
compares both full live original images with preserved backups; Android is
boot-complete with AC power connected and battery at 88%.

Diagnostic image SHA-256:
`4b31920d644a8b8c148ede06fea9efc2c5cb6710d85c03801bdbd6a9cbb02c61`.
The test writes boot only, observes USB, then restores original boot and
verifies complete boot/recovery readbacks before one bounded trace retrieval.
The physical reader remains 128 bytes; Android filesystems stay unmounted.
No Android boot is claimed from these checks.

## Physical result

The single bounded snapshot has valid format 2 and fresh cookie `0x584d0013`.
Phase `0x421` records successful init exec. The first-fatal word is zero;
the entry words are intact (no `USF1` user-fault record), and there is no
`XIT1` init-exit record or panic-prefix record. The earlier SIGSEGV/init-death
record is absent after the static-runtime correction. The corrected memory
zone still ends at PFN `0x2e800`.

This supports progress beyond the previously recorded diagnostic startup
failure. It does not prove a continuously running shell or completed report:
the current trace has no post-exec heartbeat or mount-completion checkpoint.
Userspace could be blocked, and a failure outside the instrumented paths
would not necessarily be recorded. No expected gadget/report was seen by
the guest; the operator also reported no new gadget in VMware. USB probe
success, eMMC discovery and Android startup remain unverified.

After the observation, original boot was restored before retrieval. Both
complete original images match their readbacks. Exactly one unchanged
128-byte snapshot was retrieved; Android retained its boot ID and no new
kernel fault appeared during retrieval. Recovery, partition layout and
Android filesystems were not written by the diagnostic.

## Next validation stages

1. Add a post-exec PID 1 activity checkpoint independent of USB, and capture
   PHY/UDC probe entry, stage and return status. Keep first-fatal priority,
   matching-header/cookie guards and the existing 128-byte reader; avoid
   presenting a driver merely being linked as evidence it probed.
2. Locate USB's first failed/deferred stage: PHY registration, clock/PHY
   power-up, ChipIdea creation, gadget binding and pull-up. Compare actual
   results against the working Xoom's GPIO/pinmux and power sequencing
   before changing electrical settings.
3. Once USB logs work, verify the running kernel identity and obtain the
   diagnostic RAM report, then compare eMMC/BigPart geometry read-only with
   the preserved working layout. Do not mount Android partitions yet.
4. Advance to the Android init/device-path and graphics compatibility gates
   in [the Android boot plan](android-boot-gates.md), then validate display,
   input, Wi-Fi and power management in separate stages.

The minimal UP/no-L2/no-DVFS diagnostic configuration stays in place until
there is a reliable runtime observation channel. A Motorola logo on this
display-disabled profile does not distinguish an idle diagnostic from a hang.
