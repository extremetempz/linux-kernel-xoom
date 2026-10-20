# Candidate 17: real Tegra USB PHY and explicit init-exit status

Tested 20 October 2026. The fresh trace records successful init exec followed
by PID 1 dying with SIGSEGV (wait status `0x0000000b`, no core flag). Android
did not boot under this candidate. Original boot and recovery images were
verified byte-for-byte after restoration; the working ROM remains running.

## Corrections and retained limits

The donor tied its Tegra USB PHY object to the EHCI host Kconfig option.
Earlier Wingray peripheral-only configs requested `USB_TEGRA_PHY`, which did
not exist in this donor, leaving the real PHY unbuilt. Its UDC PHY lookup
compiled to an unconditional `-ENXIO` stub after board matching.

Patch 0025 adds the real Tegra PHY option with its PHY/ULPI dependencies,
builds the PHY under that option and makes EHCI select it. This permits the
existing ChipIdea UDC to use a PHY without enabling host controllers. The
resolved diagnostic config and linked `tegra_usb_phy_probe`,
`tegra_udc_probe` and `devm_usb_get_phy_by_phandle` are checked explicitly.
Their presence does not establish successful probing or USB enumeration.

Patch 0026 records PID 1's actual wait status immediately before its specific
init-death panic. A tagged record reuses the four post-paging metadata words,
preserves an earlier non-panic fatal PC and preserves the first init-exit
record. The ordinary panic-prefix helper leaves this structured status
intact. The decoder reports normal exit status or terminating signal/core
flag, without expanding the 128-byte reader or adding a physical read.

Patch 0027 gives this candidate fresh cookie `0x584d0011` and enables SWP
emulation, matching the captured working kernel's legacy userspace setting.
This is compatibility alignment; candidate 16 did not capture a signal or
instruction proving SWP caused its init exit. NEON remains disabled.

UP mode, disabled L2/DVFS/suspend, the corrected lowmem cap, runtime trace
readiness guard and video/console reservations remain. The diagnostic RAM
disk mounts only virtual filesystems. Android data and partition layout
are not changed by this test.

## Verification and hardware procedure

The diagnostic build passes ARM/DT/config and boot-image checks with real
PHY symbols linked. Eleven compiled init-exit cases verify status values,
readiness/header guards, bounded writes, signature ordering, preservation
of a prior fatal PC and preservation of the first exit record. Eleven panic
prefix cases include preserving the structured exit status; eight compiled
post-init exec cases run with init memory inaccessible. Prior fatal and
memory-sizing regression checks pass. The full peripheral control build
also passed with the actual PHY linked, checking the dependency change
outside this diagnostic profile.

After original boot/recovery readback and power verification, perform the
authorized boot-only test. Capture USB serial if it appears; otherwise
restore the original boot, verify both images and Android, then retrieve one
bounded trace. An exec-success marker is an early userspace milestone, not
proof that Android has booted.

## Physical result and controlled runtime check

Preflight verified both complete original images and AC power before the
authorized boot-only flash. After more than two minutes, no expected USB
serial gadget was seen in this VMware guest. This is not proof that the
device failed to enumerate on the host or that a particular USB probe failed.

The single bounded 128-byte snapshot has matching cookie `0x584d0011`, valid
header and phase `0x421` (`init_exec_succeeded`). Tag `XIT1` records PID 1's
actual death status `0x0000000b`: signal 11, without a core flag. The fatal
marker is panic, not a captured kernel instruction fault. This establishes
an init-death panic after exec; it does not locate the userspace faulting
instruction or establish that USB initialization succeeded.

The original boot image was restored before trace retrieval. Full boot and
recovery readbacks, transferred in 1 MiB chunks and compared with their
preserved originals, matched. Retrieval used one unchanged bounded mapping;
Android's boot ID stayed unchanged and no new kernel warning/fault appeared.

As a separate control, the exact BusyBox, linker and library closure were
extracted from the prepared archive, hash-verified on the restored device
and run in a temporary isolated root on its working kernel. A shell, uname
and true completed with status zero. No filesystems were mounted, and only
the newly created temporary files/directories were removed afterward. This
checks the copied runtime's basic viability; it does not reproduce PID 1's
environment or prove the same runtime works under this 4.4 kernel.

The next candidate will capture PID 1's first ARM userspace page-fault PC,
address and status before signal delivery. The observed SIGSEGV does not
justify a speculative graphics, storage or SWP fix.
