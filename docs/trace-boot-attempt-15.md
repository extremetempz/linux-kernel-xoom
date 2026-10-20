# Candidate 15: panic prefix, init progress, USB and storage diagnostic

Prepared 20 October 2026 after candidate 14 passed early memory setup and
recorded a later panic. The boot-only two-minute observation, original restoration and bounded trace
retrieval are complete.

## Changes

The verified lowmem correction remains unchanged. Dedicated diagnostic config
and DT retain UP mode, disabled L2 driver, disabled DVFS/suspend, fixed video
and console reservations and no early UART polling. Enable only USB
peripheral/PHY and serial gadget, the two Xoom USB GPIO hogs, eMMC/SDHCI and
the existing Xoom BigPart in-memory partition view. Display, touch, network
and PMIC probes remain excluded. The diagnostic RAM disk mounts only virtual
filesystems and does not mount Android system/data/cache.

New coarse phase markers bracket IRQ/timer/console setup, kernel-init entry,
basic initcalls and init execution. An init execution error records its errno;
a successful exec records a distinct phase before returning to userspace.
These markers do not establish Android framework or UI startup.

After panic text is formatted, a guarded helper stores at most its first 12
bytes in the existing four post-paging metadata words. It publishes `PNC1`
only after the bytes are stored. This intentionally replaces active-zone
metadata after panic, while retaining the phase, fatal word and earlier
stage markers. No trace expansion, new physical-memory reader or extra
mapping is involved. The helper checks readiness, magic, version, cookie,
first-fatal type and prior message; it allocates nothing and takes no lock.
It does not insert operations into an exclusive-access sequence.

Fresh cookie: `0x584d000f`. Donor instrumentation commit `668ccec8`; diagnostic
profile commit `135f41fe`, exported separately as patches 0021 and 0022.

## Offline validation

The diagnostic kernel and trace-disabled control both build and pass
image/DT/config verification. The
actual compiled panic helper passes ten cases covering empty/short/exactly
12-byte prefixes at a mapped-page edge, readiness/magic/version/cookie guards,
non-panic first events, write bounds, signature-last ordering and preservation
of an existing prefix. Nine prior fatal-entry cases and 48 MMU snippets pass;
converter and start-kernel checks pass. The decoder covers old records, zone
metadata, panic replacement, truncation and init exec status. BigPart tests
pass, including 1000 capacities. These checks do not prove hardware USB,
eMMC or Android functionality.

## Test plan and result

Read-only preflight verified AC charging, completed Android startup and full
original boot/recovery readbacks. Fastboot accepted the boot-only diagnostic
write and reboot. Observe USB enumeration and,
if serial appears, collect the RAM-disk report and kernel log without mounting
Android filesystems. If the diagnostic stops, restore the original boot image,
verify full boot/recovery readbacks and Android startup, then retrieve one
bounded trace with the new cookie. Keep raw runtime, logs and images local.

Kernel-plus-DTB SHA-256:
`4abf6864924076b05f53ecf8354588271aebb1f17b6849f7ebb7ad24aac11e07`.
Diagnostic-image SHA-256:
`084d57acd3a04d60ddd294ed19b47ad0442ee481be46ab6ac277de052dbeefeb`.

During the two-minute observation this VM did not see a USB serial gadget.
That observation does not establish whether the kernel bound a UDC on the
tablet: VMware may require a new-device handoff. The absence of host USB does not establish successful or failed storage
probing. No new-kernel filesystem mount was attempted.

## Verified hardware result and diagnostic defect

Android returned on the original Linux 2.6.39.4 kernel after restoration.
Full boot and recovery readbacks match the preserved originals. One bounded
snapshot returned a valid format-2 record with cookie `0x584d000f`; Android's
boot ID was unchanged, its kernel log did not change and the temporary reader
was removed. Raw evidence remains private under
`artifacts/trace-boot-attempt-15-prepared/`.

The Normal zone still ends at PFN `0x2e800`. The last phase is `0x411`,
`basic_setup_returned`. The first fatal PC is `0xc02cd2ec`, which resolves in
the exact build to `of_get_flat_dt_root()` in `.init.text`. There is no panic
prefix because the first event is a kernel die PC rather than the panic
sentinel; preserving that first event is intentional.

Source review found a defect in the new late init-exec diagnostic hook:
`run_init_process()` is called after `free_initmem()`, but its static trace
helper called flat-DT functions marked `__init`. Those functions' code has
already been released/poisoned at that point. The offline compiled init-exec
fixture makes the init section inaccessible and reproduces the old fetch at
exactly `0xc02cd2ec`, before the actual exec operation. This links the captured
PC to a reproducible diagnostic defect. Do not treat this as an Android
userspace incompatibility or a USB-driver diagnosis.

Candidate 16 replaces the runtime flat-DT check with the persistent readiness
flag set only by Wingray's mapping callback. It must pass the same compiled
fixture with init memory inaccessible before another hardware test. This
correction does not explain candidate 14's earlier panic; a subsequent
independent startup failure may still need diagnosis.

Restoration hashes: boot
`64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`,
recovery
`5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.
