# Motorola host-only diagnostic image prepared

24 October 2026. **Prepared locally; not flashed.** This is the next isolated
hardware test toward graphics, not an accelerated Android image. Existing
hardware-tested configurations/DTs and both original backup images are preserved.

## Exact candidate

- Kernel revision: `58e4878b`, Linux 4.4.147, local release `-wingray-host-test`.
- Image: `artifacts/host-image45-v2-ready/wingray-host-diagnostic.img`.
- Size: 3,299,328 bytes, below the 8 MiB boot-partition limit.
- SHA-256: `31b527f6d335645a2d7f57d5d30867c123f31875e41b2f569c08eaf45a59a203`.
- Kernel/config/DT evidence: `artifacts/wingray-host-test45/`.
- `45` identifies this preparation checkpoint, not a completed hardware attempt.

The original boot and recovery backups were SHA-256 checked before and after
packaging. Their recorded hashes still match. There was no USB operation,
reboot, flash, partition write or storage mount during this preparation.
Live boot/recovery partition readback is still required before a future flash;
backup-file checks do not substitute for live readback.

## What this test activates

The profile inherits the physically tested allocator resource DT. It changes
only the model and host1x status/compatibility/clock-name properties. It uses
the donor's `nvhost-bus` population path and the existing Tegra 2 auxiliary
resource table; the ordinary platform-host binding would not register this
legacy driver correctly.

The host register range is `0x50000000 + 0x24000`, with syncpoint/general GIC SPI
65/67, CAR clock/reset 28, and named clock/reset `host1x`. These are inherited
Tegra 2 resources; the original Motorola source comparator also identifies
host1x clock ID 28. This is source/compiled-DT correspondence, not physical
confirmation of interrupt behavior.

The optional diagnostic acquires only the existing host clock and preserves
its firmware rate. It does not set an engine frequency or voltage. With the
host clock enabled, probe obtains and deasserts only the host reset, checking
the result; it does not pulse reset. Existing host probe then initializes its
syncpoint/IRQ infrastructure with the checked clock interval.

At late init, a fixed kernel test makes three checked host activation/suspend
cycles, verifying a nonzero unchanged host rate, IRQ-started state during
activation, and zero module references/stopped IRQ state after suspension.
It logs `XOOM_HOST_TEST_BEGIN`, three `XOOM_HOST_TEST_CYCLE ... PASS` records and
`XOOM_HOST_TEST_PASS`, or a specific `XOOM_HOST_TEST_FAIL`.
The test contains no command buffer, engine submission, syncpoint-increment
job or GPU microcode. Successful IRQ registration does not prove that a real
GPU completion interrupt was delivered.

All host child nodes, including GR2D, GR3D and both DCs, remain disabled. GART,
IRAM allocation, AVP/media, system-memory nvmap heaps, modern DRM ownership,
CPU frequency scaling and suspend-to-RAM remain excluded. The generic 256 MiB
nvmap reservation and all tested power/pinmux/USB/storage/touch properties are
unchanged. No Samsung power or display settings were imported.
The downstream shared-EMC aliases and DVFS object are omitted only for this
explicit host-test option (and the existing resource-only option). Ordinary
legacy configurations retain their existing behavior.

## Separate kernel corrections

- Patch 0088, `80f09650`: module suspend now returns a failed power transition
  before invoking its success callback. Its existing callback remains void.
- Patch 0089, `c156c0f9`: nvhost DT recursion skips disabled children without
  dropping the iterator's reference twice; real child errors are propagated.
- Patch 0090, `58e4878b`: separate host-only Kconfig, DT, defconfig, clock policy,
  checked reset deassert and fixed diagnostic loop. No tested profile is edited.

The new source patches replay exactly from `f9bcb77a`, and changed files match
the compiled mirror. Existing Wingray DT/config sources were compared against
that revision and are unchanged. The manifest records their individual hashes.

## Offline checks passed

A full ARM kernel link, zImage compression and three compiled DTs pass.
The two control DTs are the allocator resource profile and tested SMP2 profile.
The new validator allows only the exact host-only delta, checks the inherited
reservation and requires every direct host child to remain disabled.
Nineteen unsafe DT/config mutations are rejected. Actual Kconfig resolution
also excludes the host-test option when legacy DC or CPU frequency is enabled.

Extracted actual-function fixtures cover the fixed three-cycle loop, activation
failure, excluded resources, suspend-error propagation and DT child-reference
lifetime. Clock initialization fixtures verify that this option performs no
clock rate-setting/enabling operations during initial clock acquisition;
probe/runtime subsequently enable clocks explicitly and check the results.
Existing runtime, clock, IRQ, probe, allocator-EMC isolation, publication and
submission regressions also pass. These fixtures use provider mocks, not the
Xoom hardware.

The image uses the existing standalone static BusyBox RAM diagnostic and framed
USB report service. The report includes host nodes, virtual resource/IRQ data
and fresh kernel logs. There are no vendor libraries or Android startup. Only
virtual filesystems are mounted. Header addresses match the preserved boot
layout: kernel `0x10008000`, ramdisk `0x11000000`, tags `0x10000100`, page 2048.
The exact appended DTB, image SHA-1 ID, SHA-256 and RAM-disk contents pass checks.
Saved base-image files in that output folder are packaging evidence; the
candidate is specifically **wingray-host-diagnostic.img**.

Reproduce into fresh output directories:

```sh
XOOM_PROFILE=host-test XOOM_ARTIFACT_DIR="$PWD/artifacts/new-host-kernel" bash scripts/build-wingray.sh
python3 scripts/prepare-host-diagnostic.py --kernel-dir artifacts/new-host-kernel --output-dir artifacts/new-host-image
python3 tests/test-host-diagnostic-profile.py artifacts/new-host-kernel artifacts/new-host-image
```

## Planned physical test

First verify the working ROM, battery and complete live boot/recovery hashes
against the preserved originals. Flash only the exact candidate to boot after
the USB fastboot handoff. Keep recovery and the partition layout untouched.
The expected display is the firmware Motorola screen, not Android Welcome;
USB diagnostics and the cycle records determine the result.

Collect two fresh USB reports, checking the exact kernel release, host pass/fail
records, IRQ registrations and absence of enabled engines or kernel faults.
Then restore the original boot image, start the working ROM and verify both
complete original partition hashes again. If USB never appears, use fastboot
to restore the original before investigating the failure. No partition erasure,
repartitioning or recovery write is part of this test.

A host-test pass would establish initial host clock/IRQ activation and lifecycle
behavior only. EMC-rate validation, engine power/reset resources, actual blob
submission format, GPU render/readback and accelerated composition remain
separate gates. Wi-Fi, Bluetooth and charging remain queued as previously agreed.
