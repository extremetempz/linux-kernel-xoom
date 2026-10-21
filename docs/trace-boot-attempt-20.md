# Candidate 20: post-exec mount activity and USB probe status

Tested 20 October 2026. A valid fresh trace confirms a mount syscall from
PID 1 or a direct child returned zero, and both USB PHY and UDC probes
returned zero. No fatal event is recorded. USB enumeration was not observed.
Original boot/recovery readbacks match after restoration; Android is running.

The image is unchanged from the build-only request. SHA-256:
`822d07ab09677bed3fc057c704c4d4757fa9447934a0d58b4af29a8a116c09a1`.
Fresh trace cookie: `0x584d0014`. Donor commits `32291dfb` and
`e74b90be` are preserved in patches 0031 and 0032 and the local two-commit
patch bundle. The static ARM runtime and electrical settings are retained.

## Instrumentation and limits

Before normal driver initcalls, a guarded `DIA1` record replaces the
post-memory scratch words within the same 128-byte trace. Separate slots
retain the latest USB PHY probe status, UDC probe status and a mount-syscall
status from PID 1 or a direct child. Init's BusyBox mount utilities run as
children, so observing PID 1 alone would miss those calls.

Probe statuses distinguish entry, selected stages, return success and
encoded negative errno (including deferred probing). Success means the
instrumented probe returned zero, not that USB enumerated. The existing UDC
PHY-resume return handling is unchanged; its marker records an attempt.
Mount return success proves one scoped syscall completed, not that the
whole script, report or Android framework started. Statuses describe the
last attempt; deferred probes can retry.

Readiness, magic/version/cookie and first-fatal guards protect the scratch
stores. Panic and init-exit records retain priority. No allocation, DT walk,
user-pointer read or expanded physical read is introduced by these helpers.
The diagnostic profile remains UP, without L2/DVFS/suspend or display probes.

## Offline checks already completed

The kernel/DT/config build and measured Android boot-image layout pass.
Fifteen cases execute the actual compiled diagnostic helpers with init
memory inaccessible, checking bounded slots, publication order, encoded
errors and guard/preservation behavior. Ten user-fault, eleven init-exit,
eight init-exec and decoder regressions pass. The clean donor contains the
complete committed patch series.

## Authorized hardware procedure

Verify exact device identity, power and complete original boot/recovery
readbacks; test only boot; observe for two minutes and collect USB serial if
available. Restore original boot and verify both complete original images
before one unchanged bounded trace retrieval. Recovery, partition layout
and Android filesystem writes remain outside this diagnostic.

## Observation and restoration

The two-minute observation produced no expected serial gadget/report in the
guest. The operator also reported no new gadget in VMware. After the
operator returned to fastboot, original boot was restored and the device
rebooted to Android. Both complete original-image readbacks match their
preserved backups. Exactly one unchanged bounded 128-byte snapshot was
retrieved; Android retained its boot ID and no new kernel fault appeared.


## Physical result and remaining limits

The fresh format-2 record has cookie `0x584d0014`, `DIA1` scratch signature
and raw value `0x2` in all three slots: USB PHY probe returned zero, UDC probe
returned zero and the latest observed mount syscall from PID 1 or a direct
child returned zero. Phase `0x421` remains init-exec success; first-fatal is
zero. There is no userspace-fault or init-exit record.

This establishes actual activity after exec, advancing beyond candidate
19's coarse milestone. The mount trace does not identify which filesystem
or show that the complete script/report finished. The diagnostic script
mounts only virtual/RAM filesystems. Android filesystems were not mounted
by the diagnostic.

Probe success establishes neither gadget-driver binding nor enumeration
or correct electrical operation. In particular, the UDC's existing
`usb_phy_set_suspend(..., 0)` return value remains unchecked by the original
driver, as noted before the test. A zero UDC probe result does not prove
that resume call succeeded. Gadget binding, PHY resume, VBUS detection and
pull-up/connect sequencing are the next observation points; no cause is
assigned without further evidence.

The authorized build 20 cycle is complete. No new image, background monitor
or further device test is started as part of this result.
