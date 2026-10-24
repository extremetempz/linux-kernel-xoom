# Checked graphics runtime and submission integration

24 October 2026. No device access, reboot or flash. No boot image was made.
The existing hardware-tested configurations, DTs and original images are
unchanged. This stage modifies Decatf's existing driver rather than introducing
a replacement engine or importing Samsung board power settings.

## Implemented source changes

Patch **0086**, kernel commit `6a4869ad`, fixes an error-pointer free discovered
by fault-testing the actual submit function. When context-save preparation
fails, the error is retained but the pointer is cleared before common cleanup.

Patch **0087**, kernel commit `f9bcb77a`, connects checked runtime activation to
command submission:

- `nvhost_module_busy_checked` acquires a module reference only after successful
  activation. Its callers return the error without issuing a matching idle for
  a reference they did not acquire.
- Parent host activation is checked before enabling engine clocks. EMC rounding
  uses a signed result, rejects zero/negative rates, and propagates vote errors.
  Clock failure unwinds enabled clocks in reverse order, attempts to restore the
  prior EMC vote and releases the parent reference. Rollback failure is logged
  while the original activation error is preserved.
- The host clock-on callback now returns IRQ-start errors. A failed callback
  prevents RUNNING state and stops the main submit path before syncpoint access,
  context setup or CDMA command publication. A pending context-restore flag
  survives failed activation so a later successful retry cannot omit restoration.
- The main host1x submit, 3D-register command path, direct register read/write,
  keepalive channel acquisition, clock-rate read, host mutex acquisition and
  uncached syncpoint wait use checked activation. Failed keepalive acquisition
  tears down a newly created CDMA instance and preserves an existing channel.
  The submit path also removes its duplicate busy notification.
- Power-sequence failures propagate through activation and initialization.
  Failed power-off does not advance the software state. Power-off no longer
  disables the already gated module clock a second time. Failed clock-off is
  retried rather than followed by power-off.

## Verification

Four new fixtures compile extracted, actual donor functions with provider
mocks and undefined-behavior checks:

| Fixture | Faults and behavior exercised |
|---|---|
| `test-nvhost-runtime-activation.py` | Parent and each engine clock, EMC negative/zero rounding, failed vote and rollback, parent/engine IRQ errors, power-up failure, reference balance, repeated activation and context-restore retry |
| `test-nvhost-submit-activation.py` | Failed activation performs no syncpoint/CDMA access; six early error paths and successful submit; catches the error-pointer cleanup bug |
| `test-nvhost-power-sequence.py` | Missing reset provider, sequence/power-off errors, successful clock-reference balance and no duplicate disable |
| `test-nvhost-keepalive-activation.py` | CDMA allocation and activation errors, retry, existing-channel preservation and exclusive-channel rejection |

Existing clock-initialization, IRQ, host-probe, control-device, syncpoint-sysfs,
channel-publication, submission-stream, shared-EMC vote and resource-only EMC
regressions also pass. These are host/provider fixtures, not hardware tests or
proof of interrupt timing, DMA coherency, concurrency or DRAM stability.

A full ARM `vmlinux` link passes with the existing full-graphics compile
configuration, unchanged from checkpoint 43. All eight changed source files
match the build mirror; patches 0086/0087 replay exactly from `dc9bb672`.
`nvhost_module_busy_checked` is present in the linked image. Private artifact
`artifacts/graphics-runtime44/manifest.json` records revision, source/output
hashes and limits; the final build log explicitly records the changed objects
and final link. This is compile evidence, not a flashable graphics candidate.

## Remaining boundaries

This implements runtime error propagation and submission readiness for the
converted entry points. It does not supply or validate Motorola-specific EMC
rates/DRAM timing tables, reset ownership, power rails, engine DT resources or
the installed NVIDIA blob's actual submission dialect. The donor's existing
reset helpers and PMC sequence still contain unchecked reset operations;
these must be reviewed before enabling the engine profile on hardware.
The normal engine initialization/unwind path also remains a separate task.

Legacy void `nvhost_module_busy` consumers outside the converted entry points
retain their reference semantics and log activation failures. They cannot all
return an error without changing their interfaces. Consequently this is not a
claim that every control/debug/display consumer is safe after provider failure.
The context-save power-off callback runs under the module lock after checked
activation; recursively calling the new busy helper there would deadlock.

The idle EMC vote path and global EMC alias registration still require review.
Successful source-level error propagation does not authorize guessed rates or
Samsung board tables. No accelerated Android profile or new boot image is
approved by these tests.

The next evidence gate remains Motorola resource/provider validation, followed
by the already validated vendor-EGL offscreen test on Linux 4.4. Posting,
completion/fences and HWC integration follow successful offscreen readback.
**Linux 4.4 GPU acceleration remains unproven.** Wi-Fi, Bluetooth and charging
remain queued after the six previously agreed areas.
