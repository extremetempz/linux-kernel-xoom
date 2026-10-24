# Initial Motorola host clock/IRQ hardware result

24 October 2026. The prepared host-only diagnostic was flashed to **boot only**
and executed on the MZ604 Wingray P3. No recovery write, repartition or erase
was performed. This is one physical boot with three host lifecycle cycles,
not three independent boots and not a GPU-rendering test.

Candidate SHA-256:
`31b527f6d335645a2d7f57d5d30867c123f31875e41b2f569c08eaf45a59a203`.
The candidate and original backups passed preflight; the original Android
kernel was running, boot complete, with 68% battery. Both complete live boot
and recovery hashes matched the preserved originals before flashing.

## Observed evidence

Two independent framed USB captures have different request nonces and advancing
uptime, verified report integrity and matching full disk capacity/ten BigPart
partition extents. Both show Linux `4.4.147-wingray-host-test`, the expected
host resource registration, `/dev/nvmap` and `/dev/nvhost-ctrl`.

The kernel reports:

```text
XOOM_HOST_TEST_BEGIN rate=150000000
XOOM_HOST_TEST_CYCLE 0 PASS
XOOM_HOST_TEST_CYCLE 1 PASS
XOOM_HOST_TEST_CYCLE 2 PASS
XOOM_HOST_TEST_PASS cycles=3 rate=150000000
```

The checked loop confirms unchanged 150 MHz host rate, successful IRQ-start
state while active, and stopped IRQ state/zero references after each suspend.
The final ACM reference count in both reports is zero. Host IRQ registrations
are absent from the later `/proc/interrupts` snapshot because the final cycle
has suspended the host; this is expected, not evidence of failed registration.

No `BUG:`, `Oops:` or kernel-panic record was observed in either capture.
A sysfs warning identifies the donor's `fsync_enabled` parameter permissions
as invalid `0755`. The same warning is present in both preserved attempt-40
cached-sharing reports; source `fs/sync.c` still uses that mode. The warning
remains unresolved and should not be described as a warning-free boot.

## Limits and next gate

This establishes an initial physical pass of checked host activation/suspension
at the firmware's existing clock rate, with USB and storage reporting intact.
It does not test delivery of an actual GPU completion IRQ, engine power/reset,
EMC rate transitions, command submission, DMA coherency, rendering, display
composition or a new Android boot. No GPU job was issued. The original tested
Android/SMP/display/touch configurations were not changed.

The next graphics gate remains Motorola engine and EMC resource validation,
then the matched vendor-EGL offscreen render/readback test. A host-only pass
must not be presented as completed acceleration.

## Restoration

The original 8 MiB boot image was flashed back successfully and the working
original Android kernel and boot completion were observed. Normal Android USB
disconnected during the first verification attempts. After reconnection, both
complete live partition hashes matched the preserved originals:

- Boot: `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Recovery: `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.

**Restoration and full verification are complete.** The candidate is no longer
installed. Recovery was never written and no further flash was performed.

Private raw reports and flash/restore logs are retained under
`artifacts/host-test45-report-a`, `artifacts/host-test45-report-b` and
`artifacts/host-test45-attempt1`; they contain device identifiers and are not
published. The prepared artifacts remain unchanged.
