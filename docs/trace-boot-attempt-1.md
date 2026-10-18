# First instrumented physical boot — 18 October 2026

**The new kernel did not complete boot. Its entry instrumentation did execute,
and the trace survived restoration and return to Android.** The original boot
image has been restored and verified byte-for-byte on the device. Recovery
also still matches its original backup byte-for-byte.

## Test and recovery

The user explicitly approved flashing this candidate to boot, testing it,
restoring the original and retrieving its trace. Fastboot identified the
expected xoom-wifi product and bootloader 1050. It successfully wrote the
1,767,424-byte candidate, SHA256
`5e3dadb0ef1c21aa84787cd215af856bf7742c7181cd9fea891dd5eeb70d3d6a`.
The candidate was observed for approximately 30 seconds, then the user returned
it to fastboot with the hardware buttons. The user confirmed that fastboot was
ready but did not provide a specific candidate-screen description; do not infer
one from that reply. USB is deliberately disabled in this minimal profile.

Fastboot successfully restored the full original boot image and rebooted it.
The user confirmed Android returned. Subsequent device readbacks matched:

- Boot: `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Recovery: `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.

No recovery flash or partition-layout change occurred. One bounded read-only
mmap retrieval returned 128 stable bytes with exit status zero. The legacy
Android ADB stream was base64 framed with an explicit remote exit trailer.
Android's boot identifier stayed unchanged through retrieval, and ordinary
kernel-log comparison found no new fault markers. The temporary reader was
removed. Raw images, trace bytes and runtime logs remain ignored/local under
`artifacts/trace-boot-attempt-1/`; they are not uploaded.

## Verified trace observations

The record matches magic `0x584f4f4d`, format 1, build cookie `0x584d0001`.
The prior working-ROM preflight had no valid record, and this is the first
approved execution of this trace build. Captured entry values are:

| Field | Value |
|---|---|
| PC captured by entry `mov r3, pc` | `0x00a008d0` |
| r0 | `0` |
| r1 | `0x0a49` (2633, legacy STINGRAY) |
| r2 | `0x00000100` |
| CPSR | `0x000000d3` (ARM SVC, IRQ/FIQ masked) |

The normalized-mode, ATAG-conversion, pre/post-decompression, kernel `stext`,
pre-MMU, Tegra `init_early` and early-initcall markers are all absent. The ATAG
return field retains its not-yet-called sentinel. SCTLR and CPUID fields remain
zero from record initialization; **they were not captured and must not be
interpreted as actual register values.**

The `mov r3, pc` is at zImage offset `0xc8`, yielding ARM PC value base+`0xd0`.
The observed PC therefore implies an execution base of `0x00a00800`, despite
the header declaring kernel load `0x10008000`. Similarly, observed r2 is `0x100`,
not the header's declared `0x10000100`. These distinguish measured entry values
from header declarations. MMU state was not captured, so the PC-derived base is
not independently proven to be a physical address. The ATAG contents have not
been inspected. These observations alone do not establish a bootloader defect.

This establishes retention for this one button-reset → fastboot → original
restore → Android sequence. It does not prove retention for other resets or
guarantee that every later marker would survive. No exact fault PC was captured.

## Separate instrumentation correction

Inspection found a real defect introduced by patch `0005`, independent of the
unresolved original peripheral-kernel failure: entry trace `ldr =constant`
instructions create a literal pool in the `.start` input section. On switching
to `.text`, the linker places that pool at the end of `.start` directly in the
fall-through execution path. The tested binary has data words at offsets
`0x170..0x17f`. The first word, `0x1fe00000`, encodes an SVC under condition NE;
the normalized SVC path has that condition true. There is no branch over it.

This defect lies between the captured entry and the missing mode marker and
could explain this attempt's stop. It is not proof of the actual hardware fault
instruction, and it cannot explain the older uninstrumented candidate's failure.
The earlier 64 tests executed isolated snippets and missed the transition
between sections. That coverage gap is corrected with an entry-to-mode test.

Source correction `fa971783`, carried separately as patch `0006`, branches
around an explicit `.ltorg` before entering `.text`. A mode-end label supports
testing the complete path, including the HYP stub and mode normalization.
The next build uses cookie `0x584d0002` to distinguish it from this attempt.

Offline checks:

- The old binary reproducibly reaches the literal pool in 32 Cortex-A9 runs:
  16 initial NZCV flag patterns at both the header and PC-derived execution bases.
- The corrected binary passes those 32 entry-to-mode runs without executing
  literal data, preserving r1/r2 as saved r7/r8 and confining writes to the record.
- The existing 64 compiled snippet tests still pass; trace profile verifier and
  boot-image audit pass. These do not simulate hardware cache/reset behavior.

Corrected kernel/DTB output is in `artifacts/boottrace-flow-fix-1`.
`zImage-dtb` SHA256:
`4535aa074c3a178718549b4e1b3cd8867eb29b4d669bde559af9cd1b57af7db0`.
A separate audited boot image is prepared at
`artifacts/trace-boot-attempt-2-prepared/wingray-diagnostic.img`, SHA256
`216616c0e894fb86041d0b970eb6e106e3beed9fd4fb0560da4e17f5de28236e`.
It has **not** been flashed or booted. Its test requires new explicit approval
for boot flash, restoration and trace retrieval. Decode it with expected cookie
`0x584d0002`; the decoder default remains the first attempt's cookie.
