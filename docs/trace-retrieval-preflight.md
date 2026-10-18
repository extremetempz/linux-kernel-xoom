# Read-only trace retrieval preflight — 18 October 2026

The user explicitly approved copying the prepared reader to a temporary Android
directory and performing one bounded read-only mapping test. **That single test
succeeded.** There was no second physical mapping invocation or retry.

## Verified result

- The connected device identified as Wingray, running the expected
  `2.6.39.4-ElementalX-Xoom-2.1+` kernel with root ADB. Its extracted config was
  byte-identical to the saved working config. The target page was outside all
  listed `/proc/iomem` resources; the adjacent upper console reservation matched
  the reviewed layout.
- Original host boot and recovery backups still matched their saved checksums.
- Reader SHA256 matched locally and on the device:
  `f6d45ea6e2b1269094599d9cdfe0ce8b8a55a23d4b6b382b7e44ddc0ff3633eb`.
- Default mode printed its no-access plan successfully before the opt-in call.
- The opt-in call mapped one page read-only and produced exactly 128 snapshot
  bytes with remote exit status zero. The reader's two bounded word-copy passes
  agreed. No physical-memory write was requested or performed by the reader.
- The legacy Android ADB shell translates binary newlines, so the snapshot and
  an explicit remote exit trailer were base64 encoded together. The host
  validated the encoding, exact decoded length, zero exit trailer and absence
  of ADB stderr before accepting the record. No `exec-out` support was assumed.
- The boot identifier was unchanged afterward, Android reported
  `sys.boot_completed=1`, and comparison of ordinary before/after kernel logs
  found no new paging-fault, Oops, panic, BUG or WARNING markers.
- The copied temporary reader and its empty directory were removed after the
  test. No boot/recovery image was flashed or overwritten; no partition layout
  or kernel source change was needed for this hardware test.

The offline decoder rejected the saved bytes as an invalid trace record. That
is expected: no trace kernel or RAM-seeding experiment was run in this test.
It does not invalidate the successful transport and does not diagnose the
original 4.4 Motorola-logo boot failure.

## What this establishes and what remains

The explicit userspace mapping path can retrieve this reserved physical page
on the installed working kernel without reproducing the earlier direct-read
panic in this attempt. This is one successful hardware preflight, not a claim
of universal physical-memory safety or repeated reliability. Keep the fixed
address, bounds, read-only mapping and no-fallback policy.

The next distinct question is whether a uniquely tagged record survives the
specific reset/recovery sequence and remains untouched by the bootloader.
Answering that requires a separately reviewed, explicitly approved RAM write
and reboot experiment. It was not authorized or performed as part of this
read-only test. A later diagnostic-kernel boot-partition test also needs its own
approval. No new flashing permission was inferred from this preflight.

Raw transport, decoded bytes, kernel logs, config and boot identifiers remain
local under the ignored `artifacts/hardware-private/mmap-preflight/` directory.
They are not uploaded. This report contains only the validation conclusions.
