# Shutdown review — 5 November 2026

Reviewed main `7dabd2e` and merged PRs #43 (head `4af0fcd`) and #44
(head `74575a8`). This review performs read-only device reporting only. No
shutdown, reboot, repair or flash has been requested from the tablet.

## Verified observations

* Combined p9 cache/p10 data Android boot and reboot are recorded by
  `54a1592`, `472fb26` and `docs/storage-final-cache-android.md`.
* The current framed report validates the same layout, both persistent mounts,
  all other storage protections and Android startup. The currently installed
  model is the existing persistent-data clean-shutdown candidate.
* GPIO 175/PV7 is claimed as `poweroff` and is physically high while awake.
  This is consistent with the isolated active-low WDI driver being installed.
  It does not prove that native shutdown has reached that callback.
* Saved Stage D inspection reports repeatedly retain `before_cache_umount`.
  They do not contain a blocked-task stack proving the kernel wait location.
* The fresh PSTORE snapshot shows a bound ECC-enabled ramoops backend but no
  previous pstore files or last-kmsg shutdown stack. Its current-boot probe
  must not be mistaken for retained failure evidence.
* Preserved p10 and p9 evidence bundles independently revalidate backup and
  filesystem health. This says nothing about current mounted filesystem
  cleanliness or poweroff completion.

## Defects and limitations in the previous inference

The last persistent marker does not distinguish a blocked umount from its
read-only-remount fallback, the next persistent marker write, or an unflushed
marker. Native init marker strings in saved evidence contain trailing stale
text (`before_scriptartt`). The FD scanner omitted cwd/root/mmap references;
its fuser command also opened its own output on /cache. Lack of a listed FD
is not proof that no reference exists. PR44's conclusion about kernel journal
teardown is therefore a hypothesis, not an identified root cause.

Shutdown diagnostic writes were going to /cache and /data after the initial
sync and around unmount/clean-state verification. Those writes perturb the
filesystem being quiesced. A marker after a failed RO transition could also
fail independently. The old timeout approach can wait indefinitely for an
uninterruptible child even after SIGKILL; a timeout command is not a guarantee
that the parent proceeds or that the storage operation was cancelled.

The Deepseek host parser replacement also dropped the explicit persistent-cache
and cache99 modes while the capture CLI still advertised them. Its combined
mode did not enforce mountinfo major:minor/root/superblock flags for p9/p10.
The retained regression tests reproduced acceptance of an incorrect device.
These parser issues do not explain physical shutdown, but weaken its evidence.

## Corrections

The shutdown service now uses a conservative RO-remount-first transaction.
Services stop as before, propagation is made private, sync completes, emulated
FUSE mounts are detached, and fixed p9/p10 ext4 devices are remounted RO with
nosuid/nodev/noatime retained. It never unmounts those physical filesystems,
uses forced/lazy unmount, or ignores a failed operation. This avoids the
unmount-first path, not a proven underlying journal bug.

This has a source-backed rationale in this exact donor: ext4_remount() syncs,
suspends quotas, sets MS_RDONLY and calls ext4_mark_recovery_complete(), which
flushes the journal, clears needs_recovery and commits the superblock. It does
not destroy the journal thread as ext4_put_super()/jbd2_journal_destroy() do.
A filesystem need not be unmounted to be clean and safe for normal poweroff.

All remaining eMMC aliases must show RO in both VFS and superblock fields.
The fixed mount identities are rechecked, final sync must succeed, and p9/p10
must have clean state, no recovery bit and zero recorded error count before
native powerctl is permitted. Metadata reads are bounded too. No physical
marker writes remain; the holder scanner now writes RAM and terminates.

Blocking commands run under a polling supervisor. If the deadline expires,
it records the worker stack and root-only SysRq-w blocked-task dump, requests
SIGKILL and returns failure without waiting for a D-state child. It does NOT
claim the child's operation was cancelled or proceed to poweroff. Diagnostic
stack reads and kernel lockups cannot be guaranteed to complete if the whole
kernel stops; software alone cannot promise recovery from every failure.

Kernel patch 0183 adds stack/hung-task/SysRq diagnostics only to the opt-in
shutdown defconfig and logs WDI callback registration/entry. No regulator,
charging, CPU voltage, GPU, display, radio, storage-policy or suspend enablement
is changed. Known-good profiles/images remain unchanged.

## Validation and release decision

Actual shell execution tests cover success for tmpfs and persistent cache,
reboot versus shutdown, wrong identities, writable aliases, VFS-only RO,
failed propagation/sync/remount/property handoff, dirty/error/recovery metadata
and a stalled worker. They require no physical cache/data unmount and no
native handoff after a failed gate. Parser regressions and the current hardware
report are checked separately. The donor's actual ext4 clean-RO function is compiled with a faulted journal
model to verify flush/clear/commit ordering and retention of the recovery bit
on flush failure. Full ARM image build and packing pass with existing evidence gates, without
bypassing protected backup checks. The final compiled-in runtime matches the
reviewed source byte-for-byte; the actual kernel streaming cpio parser accepts
it at four chunk sizes and rejects corrupt magic. Boot layout audit passes
against the original image. The image hash is
`7615b6140285cd76f82cff4b98abd3146ae007bb6a0866b1207ac62873d8bd79`
(4235264 bytes). See [offline validation receipt](../evidence/shutdown1105-offline-review.json).
It is held locally, not certified for flash.

The correction is technically justified, but successful physical shutdown is
NOT established. Remount, driver shutdown, CPU stop and WDI execution remain
hardware-sensitive. The exact old wait has not been captured. The user has
explicitly declined an experimental flash request: do not ask them to flash
this build or describe it as a verified fix based only on compile/test success.
No image is approved as a proven shutdown fix by this document.
