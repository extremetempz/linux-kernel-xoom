# Candidate89 — manual task-freezer stage, no device or CPU sleep

**Later hardware result:** [one task-freezer/thaw cycle passes](freezer-89-result.md).
The following is the original preparation record; no-flash statements refer
to development before that separately authorized test.

28 October 2026. Based on main a751e8e, following the awake wake-reference
pass in candidate88. **Built for review; not flashed. Candidate88 remains
installed. No live device request or sleep test occurred during this work.**

## Why this is the next stage

We have observed awake DC cycles and checked LIC wake-reference registration.
We have not exercised the system PM preparation/freezer, device PM callbacks,
CPU-complex sleep or physical low-power wake. Candidate89 exercises only the
first of those stages. It cannot establish deep sleep or energy savings.

A dedicated root-only `/sys/power/wingray_freezer_test` accepts exactly `1`.
The new default-off config requires the PM-preparation block and PM debug.
The isolated freezertest profile retains the candidate88 GPU, IRQ, backlight,
radio, battery, storage and ECC wiring/configuration. All ordinary
`pm_suspend()` requests and the exported device/low-level entry remain blocked;
Tegra platform suspend ops remain unregistered. No runtime switch opens them.

## Kernel changes and boundaries

Patch0162 adds an immutable `freezer_only` argument to the internal entry
function. The ordinary caller always passes false; only the separate manual
entry passes true with PM_SUSPEND_FREEZE. It requires the new option and
actual Wingray preparation mode, obtains pm_mutex, rejects any pre-existing
non-none pm_test mode, and leaves that global mode unchanged.

The test synchronizes filesystems and uses the existing suspend preparation,
PM notifier and task-freezer machinery. After successful preparation, it
records `WG_FREEZER89 tasks frozen; device/CPU suspend not entered`, waits
500ms with the kernel running, and immediately takes the normal finish/thaw
path. It returns before device suspend, CPU offlining, noirq callbacks,
platform entry, CPU power gating or DRAM self-refresh. Ordinary PM success
statistics are not incremented as if a sleep had occurred.

PM notifier callbacks DO run. This is not a side-effect-free CPU-only probe:
MMC disables rescan and invokes pre_suspend checks; its removable-card error
path may remove a card. Internal eMMC/Wi-Fi are non-removable in this DT, but
that does not validate their notifier behaviour. Bcmdhd also registers a PM
notifier; its optional features must not be assumed inert. Failure/hang and
peripheral restoration need hardware observation. No rail-state measurement
is implied by the software-stage log.

The sysfs operation uses a non-queuing mutex; status readers also return busy
rather than blocking behind the freezer and obstructing task freezing. Only
successful completion advances its counter. Errors are preserved, not silently
converted to success. The existing prepare/freezer failure cleanup remains
in use; a hard hang is not recoverable by a userspace trap.

Patch0163 separately fixes a donor defect: freeze begin/end could fall through
and dereference a missing platform suspend table, or invoke its unrelated
memory-suspend hooks when freeze hooks were absent. Freeze hooks now stay
independent and all absent-table cases are checked. The freezer-only test
stops before those functions, so this is a source-level correction for later
stages, not a claimed fix for an observed hardware crash.

## Fixed diagnostic request

FREEZERTEST invokes only the fixed `freezer-cycle` helper with no arguments.
It requires the new attribute, a clean initial result, and exact blocked-
sleep status. One write requests one kernel test. The helper checks that the
completion counter advanced by one and that no device/CPU sleep was requested.
It never writes pm_test, a sleep state, wake reference, framebuffer, GPIO or
voltage. It never retries automatically. Its exit report preserves status.

Success and failure payloads use the existing nonce/length/SHA-256/base64
transport with a 64KiB cap. Host `freezer_test_completed` is separate from
frame verification; device_suspend_tested and cpu_sleep_tested remain false.
Boot and ordinary REPORT/PSTORE/WAKETEST do not invoke this request.

## Build and checks

Apply all exported patches through0163, then use new output directories:

```sh
XOOM_ANDROID_GPU_PROFILE=freezertest \
XOOM_BUILD_ROOT=/tmp/xoom-freezer89-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/freezer89-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/freezer89-new-ready" \
bash scripts/build-android-gpu.sh
```

Final local image: `artifacts/freezer89-reviewed-ready/wingray-android44-gpu.img`.
Size **4,214,784 bytes**; SHA-256:
`edfe9c59d3f1852506efec5c89429b727ad0c8a03f4dfc1d86dff86b0d6f1015`.
Kernel head `d41358e6ec0b89c144a24c1c1633b4f8205e08eb`. The full ARM/module/
Android build passed, followed by a kernel correction rebuild and repack.
The ECC DT is byte-identical to candidate88. Final source hashes, embedded
helper/server bytes and image hash were checked; both patches replay exactly.

Offline tests execute actual entry/store functions with a stubbed freezer
engine: success/hold/finish, invalid board/config/state, busy locks/test mode,
preparation errors, counter/error accounting and absence of device entry.
They execute actual freeze/platform begin/end with null and populated tables.
They also run the actual shell helper and USB server on success/failure
fixtures. PM entry blocking, wake-arm faults, generic framed transport (20
tests), existing image validators and syntax checks pass. A separate ARM
suspend.o compile with PM_DEBUG and the new options disabled passes too.
None of these tests freezes tasks on the Xoom or proves driver restoration.

## Later single hardware test — not executed here

After code review and separate boot-only flash authorization:

1. Preserve candidate88 and complete original backup images/hashes. Keep the
   same ECC recovery reader available. Verify power, image identity and normal
   Android/USB/display/touch operation, then save fresh REPORT/PSTORE baselines.
   No repartition, recovery write or voltage change is required.
2. Require the preparation-block startup message and initial freezer counter0,
   last_result0. Do not write a system sleep state or change pm_test. Leave the
   physical power button untouched during this short test.
3. Explicitly request one test:

   ```sh
   python3 scripts/run-freezer-test.py \
     --output-dir artifacts/freezer89-cycle1
   ```

   Require a verified frame, freezer_test_completed=true, one counter increment
   and kernel frozen/thawed checkpoints. Capture a fresh normal report and
   inspect task-freezer/notifier errors. Confirm the same Android session,
   display/touch, storage, battery and radio operation. Do not infer SoC sleep
   from a paused animation or a successful task-freezer counter.
4. On failure, stop. Save evidence and use manual recovery if necessary;
   candidate88 is the matched-ECC boot-only rollback. A host timeout cannot
   thaw a hung kernel. Keep raw logs private; avoid the original2.6 logger
   until matching retained evidence is retrieved.

After this passes, the next stage is device-PM dry-run integration: checked
CPCAP wake arm/disarm in device PM ordering and the system DC/GPU restore path,
then other peripherals, before any CPU-complex sleep attempt.

## Motorola PMC audit: no guessed sleep profile

Original board-stingray selects LP0 with cpu_timer1500, cpu_off_timer1,
core_timer0x7e7e, core_off_timer0xf, COREREQ/SYSCLKREQ active-high. Original
pm.h labels the core values as LP0 ticks; pm.c writes them directly. The donor
DT fields for core timing are microseconds. No raw tick-to-time conversion or
Samsung timing was guessed or installed.

The current ECC DT still lacks complete suspend parameters, so PMC mode stays
NONE and platform entry is unavailable. The donor platform caps LP0 intent at
LP1; changing DT to LP0 would not implement original warmboot support. LP2
would power down the CPU complex while keeping DRAM active, not establish
LP1-style self-refresh. Its request polarity/clock handshake still needs
board validation. The donor tegra_suspend_enter also currently discards
cpu_suspend's return value; that must be addressed with error/unwind tests
before interpreting a later real-entry success result.

Deep sleep, physical wake from sleep, automatic Android suspend and measured
power savings remain unimplemented/unvalidated. This image is a controlled
prerequisite test, not a release of the low-power gate.
