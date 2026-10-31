# Image90 — selected CPCAP PM callbacks, hardware sleep blocked

1 November 2026. Review base main `ee3a645`, kernel patch0164 / donor
`f90fafa0`. Full ARM build and offline tests pass. **Not flashed or hardware-
tested.** No live device access occurred. The last documented installed
image is89; its current physical state was not inspected.

## Exact scope

Image90 is the first **selected-driver callback** step after89, not a full
system-device suspend test. Only CPCAP normal-phase suspend/resume callbacks
are selected. They arm/disarm one checked parent wake reference using the88
helper. They do not turn off CPCAP, alter masks/ACK, regulators, rail voltages,
SPI transport or charging controls.

Sequence on one explicit request:

1. Root-only exact `1` write; trylock the test mutex and normal PM mutex.
   Require Wingray preparation profile and global pm_test=none.
2. Existing filesystem synchronization, PM notifiers and task freezer.
3. Apply the normal PM restricted allocation mask for the callback phase,
   restoring it on return. Find the bound Motorola CPCAP on the SPI bus with its registered PM ops;
   retain a device reference and trylock its device mutex. Missing/busy devices
   fail, never wait on a device lock possibly held by a frozen task.
4. Through Linux's existing `pm_generic_suspend()` dispatch, invoke its real
   driver `.suspend` callback: verify released/unpending ON, correct LIC/ON
   domain and wake capability, then acquire the checked parent wake reference.
5. Immediately dispatch `pm_generic_resume()`: release only this transaction's
   owned reference. No intentional dwell or hardware sleep occurs. Resume is
   also attempted after suspend failure to unwind a reference retained by a
   failed arm rollback. It must never release a pre-existing manual owner.
6. Release locks/reference; use the existing suspend_finish() notifier/thaw
   path on success or callback error. Count completion only for result0.

Normal IRQ delivery, SPI parent, display, storage, USB and CPU0/1 remain
active. PM preparation notifiers still run, just as they did in89. This test
uses generic **driver** PM dispatch, not the bus's complete dpm_suspend_start
hierarchy, prepare/complete, runtime-PM accounting or late/noirq phases. It
must not be described as validation of full parent/child PM order, a whole-
device suspend, physical wake, LP2, DRAM self-refresh or deep sleep.

The callback table is compiled only for the new default-off
`MOTOROLA_WINGRAY_DEVICEPM_TEST`. It refuses invocation outside its selected
transaction. All ordinary pm_suspend(), lower-level device entry and Tegra
platform registration blocks remain. No command can release them. The
independent89 FREEZERTEST remains available with unchanged status/500ms hold.
Known-good defconfigs and DT sources are unchanged;90 adds its own defconfig.
Automatic suspend, cpuidle, DVFS, hibernation and experimental DC shutdown
remain disabled. Android's normal power-key path stays backlight-only.

## Errors and evidence

A pre-owned wake vote is refused. The checked helper owns ON mask/idle
verification; regmap-irq remains the ACK owner. The new callback tracks only
its own acquired reference, including one left by failed arm rollback.
Resume errors propagate; failure keeps ownership recorded instead of claiming
cleanup succeeded. A cleanup failure blocks further selected cycles. Preserve
the report and use explicit recovery/review; do not automatically retry or
force-clear another owner's wake references. Rebooting the matched90 image
is an operator-controlled recovery option; preserve pstore before restoring
the old ROM. No teardown/IRQ backend can guarantee recovery from hardware
failure.

Bounded process-context checkpoints are:

```text
WG_PM90_FREEZER_COMPLETE selected=cpcap cpu_sleep=0
WG_PM90_CPCAP_SUSPEND result=... owned=...
WG_PM90_CPCAP_RESUME result=... owned=...
WG_PM90_CPCAP_COMPLETE suspend=... resume=...
WG_PM90_TASKS_THAWED result=... cpu_sleep=0
```

They identify actual execution. Absence of a callback marker can mean it was
refused before dispatch/locking; read the returned error, existing wake status
and dmesg together. No CPU1-offline, L2-prepared, platform-enter or sleep-
success marker is emitted because those stages cannot execute here.

The same ECC DT as89 is byte-identical: reserved1MiB at0x1ff00000,
ECC16,128KiB records/512KiB console/128KiB pmsg. Reuse fixed PSTORE and the
matched image reader after a warm reset.84 demonstrated two corrected known-
probe recoveries, not guaranteed recovery from a hard hang or power loss.
Do not restore the2.6 kernel before reading evidence you need to preserve.

## Build and artifact

Apply exported patches through0164 to the pinned donor. Reproduce with new
output directories, existing private ROM inputs and the pinned toolchain:

```sh
XOOM_ANDROID_GPU_PROFILE=devicepmtest \
XOOM_BUILD_ROOT=/tmp/xoom-devicepm90-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/devicepm90-new-build" \
XOOM_IMAGE_DIR="$PWD/artifacts/devicepm90-new-ready" \
JOBS=6 bash scripts/build-android-gpu.sh
```

Completed local image:
`artifacts/devicepm90-reviewed-ready/wingray-android44-gpu.img`

- Size:4,218,880 bytes, below the8MiB boot partition.
- SHA-256:`4d1b2d672391b40ebe2d692762e4bc4843cfd2c5fc01e87f92c2a2be5b8dabb5`.
- Runtime/artifact directory:`artifacts/devicepm90-build`.
- Full kernel/modules, appended ECC DT and linked built-in RAM archive pass.
- The private image contains original runtime libraries; it is not committed
  to the public repo. Exported source patch and build scripts are committed.

Checks executed: actual callback/generic-dispatch ownership and injected
failures; selected/freezer dispatch; PM gates and negative config policy;
actual fixed shell helper and successful/failed nonce/hash USB frames;
20 diagnostic protocol tests; pstore bounds/framing; existing CPCAP ON IRQ,
wake-arm, LP8550 and native/all-window DC fixtures; full artifact validation. Original89 PM/CPCAP objects also compile with the
new selected-device option disabled; its config and saved image are preserved.
These are software/build checks, not physical suspend results.

## Later manual test — not executed by this work

Code review and explicit boot-test approval come first. Check original backup
hashes,89 rollback image, battery/power and physical recovery access. Only
boot may be flashed later; recovery and partition layout must remain intact.
Allow Android to settle, attach USB serial and grant the temporary host device
permission when needed. Save fresh REPORT and PSTORE before any request.
Confirm actual89-style hardware features/geometry and the initial90 status:

```text
completed=0 last_result=0 selected=cpcap whole_tree=0 cpu_sleep=0 ordinary_sleep=blocked
```

Use one fixed request only:

```sh
python3 scripts/run-devicepm-test.py --output-dir artifacts/devicepm90-cycle1
```

The host restricts the USB VID/PID, uses a nonce/length/hash-checked frame,
saves failures too, requires a counter advance and returns failure for a failed
device test. It sends no arbitrary shell, sleep state or reboot command and
never retries a DEVICEPMTEST. The helper refuses a previous failed status.

Immediately save a fresh normal REPORT and PSTORE and, through an approved
local diagnostic channel, the existing read-only `/bin/pm-snapshot`. Compare
same boot/session, CPU0–1 online, eMMC/ten partitions and ro/RAM mount policy,
CPCAP owned=0/parent_wake=0, errors and IRQ progress. Confirm on hardware that
Power off/on, complete backlight darkness/restoration, touch and GPU display
continue working; check current battery reporting and any active radio links.
Use the existing framebuffer/IRQ evidence; fb0/state0 alone is not proof.
No Wi-Fi/BT resume claim follows because their callbacks were not selected.

Pass requires a single successful counter increment, both CPCAP callbacks
returning0, clean ownership and the same healthy Android session. Failure
means stop, preserve logs, and identify before-freezer / freeze / selected-
dispatch / wake-arm / wake-release / thaw / Android-restoration stage. Do not
proceed to a whole-tree test orLP2 on failure.

## Rollback

No rollback is needed now: no device writes occurred. Preserve these files:

-89 image SHA:`edfe9c59d3f1852506efec5c89429b727ad0c8a03f4dfc1d86dff86b0d6f1015`.
- Original8MiB boot SHA:
  `64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`.
- Original12MiB recovery SHA:
  `5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.

After a later failed test, use Power+VolumeUp/manual fastboot recovery and
attach the correct USB device to the guest. Obtain matched ECC evidence
first when possible; only after explicit operator direction flash the
preserved89 or original **boot** image. Never repartition or flash recovery
as part of this test. Verify complete original boot/recovery readback when
restoring the original ROM. A successful fastboot write is not readback proof.

The remaining architecture gaps and LP2/LP1/LP0 gates are in
[suspend-lp2-dependencies-90.md](suspend-lp2-dependencies-90.md).
