# Candidate88 — combined Android awake-only wake-arming test

**Later hardware result:** [awake arm/disarm passes](wake-arm-88-result.md).
The following is the original preparation record; its no-flash statements
refer to development before that separately authorized hardware test.

28 October 2026. Based on main b524885 plus patch0161. **Built and checked
for review; not flashed.** Candidate85 remains on the tablet. No live serial
request, wake-reference change, reboot or sleep test occurred in this step.

## Purpose and scope

This integrates [checked wake-reference code87](wake-arm-87.md) into the
combined Android/NVIDIA runtime. It can test one parent IRQ wake arm/disarm
pair while the SoC stays awake. It does not enable physical suspend, Android
autosuspend, CPU voltage/frequency scaling, LP0, LP1 or LP2.

The new `wakearm` Android build selector requires the PM-preparation block,
IRQ-only CPCAP, wake-arm test, PM debug/freezer and the ECC DT. PM/SUSPEND
are permitted by image validators **only** in this complete blocked profile.
Missing block/test dependencies, automatic sleep, cpuidle, hibernation,
DVFS, new CPCAP regulators or the experimental DC resume path are rejected.
Existing no-PM profiles keep their previous restrictions and pass validation.

The new profile boots with backlight-only blanking and no wake reference
owned. It retains the original NVIDIA userspace, Wingray fixed-clock GPU,
SMP/PL310, touch, Wi-Fi/BT, battery monitor, USB and storage code/configuration.
The exact ECC DT is byte-identical to candidate85. Actual operation of this
PM-enabled combination remains hardware-unvalidated; compiling existing PM
callbacks is a change from candidate85 even though system entry is blocked.

### Configuration correction

The first attempted Android build correctly stopped because the old GPU
Kconfig condition `!SUSPEND` dropped `TEGRA_GRHOST_WINGRAY_GPU_TEST` from
preparation87. That compilation-only profile was not proof of the fixed-clock
GPU selection. Patch0161 permits it with SUSPEND only when **both** the PM
entry block and checked wake-arm option are selected. The host-only GPU
experiment retains its original restriction. No engine clocks, resets,
regulators, voltage policy or display timings are changed by this patch.
Kconfig negative controls confirm removing the preparation block drops both
the wake-arm option and the GPU exception. Apply the complete patch series
through0161 before building; there is no unconditional PM safety override.

## Fixed manual USB request

The runtime includes `wake-arm-cycle` only in the new profile. It is never
called by boot, REPORT, PSTORE or power-button events. A new nonce-checked
fixed request `WAKETEST` invokes it with no arguments. There is no arbitrary
shell command interface.

The root-only helper requires exactly one CPCAP `wingray_wake_arm` attribute
and initial unowned, parent-wake-off, error-free, sleep-blocked readback.
It writes arm once, requires owned=1/parent_wake=1/error-free readback, writes
disarm and requires owned=0/parent_wake=0/error-free readback. It never writes
`/sys/power/state`, a framebuffer, GPIO, PMIC register or voltage control.

An exit trap records the final driver status and attempts release if this
request may own a reference, including a failed arm with failed kernel
rollback. Cleanup status is preserved. A kernel/transport hard hang cannot
be repaired by this shell trap, nor can it handle SIGKILL or power loss.
A missing or pre-owned attribute fails before any arm attempt. It never
clears another owner's reference deliberately.

The server frames success **and failure** payloads, capped at64KiB, with the
request nonce, length, SHA-256 and base64 encoding. The host sender saves
verified wire/payload/status privately. `wake_arm_commands_completed` is
separate from framing success; `physical_wake_validated` remains false.
An error stops the test; no automatic repeat, suspend, reset or flash follows.

## Reproduce and review

```sh
XOOM_ANDROID_GPU_PROFILE=wakearm \
XOOM_BUILD_ROOT=/tmp/xoom-wakearm88-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/wakearm88-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/wakearm88-new-ready" \
bash scripts/build-android-gpu.sh
```

New output directories are required. Prepared local image:
`artifacts/wakearm88b-ready/wingray-android44-gpu.img`.
Size **4,214,784 bytes**. SHA-256:
`f5eca1470eb34d26ea163d82259152e4a26e11870b35e834077485e0beacd570`.
Kernel source head `d7ccf2fb` (patch0161); patch0160 contains wake-reference
ownership/rollback and patch0159 contains the mandatory sleep-entry block.
The image is under the boot partition limit and carries the built-in Android
RAM runtime, unlike the empty compilation-only images86/87.

Passed: full ARM kernel/modules/image build; required configuration and
negative controls; actual PM entry block, ON handler and wake-arm fault tests;
actual fixed helper success/missing/pre-owned/readback-failure cleanup tests;
actual USB server framing of success/failure payloads; generic framed-protocol
regressions (20 tests); candidate85 retained-console/display-scope regression
checks; complete artifact validators for new and old profiles; shell syntax.
Source/image hashes, packed executable helper/server bytes and identical ECC
DT were checked. Exported patch0161 replayed exactly against its parent.
These are offline checks, not Android boot, radio, wake or sleep validation.

## Later hardware test — not executed here

1. Preserve candidate85 and both complete original backups. Review the code
   and separately authorize boot-only flash. Verify original hashes/power
   before any write. Do not overwrite recovery or change partitions.
2. After candidate88 boots, first verify the normal Android/USB/display/touch
   baseline and capture REPORT/PSTORE. Require the blocked-PM startup message,
   correct image/runtime identity and unchanged storage policy. Do not send
   sleep-state writes even if a generic state name is advertised.
3. Explicitly run one test:

   ```sh
   python3 scripts/run-wake-arm-test.py \
     --output-dir artifacts/wakearm88-cycle1
   ```

   Require verified frame, `wake_arm_commands_completed=true`, final owned=0,
   parent_wake=0 and zero errors. Inspect failure/cleanup fields before any
   retry. Check normal power-button events, touch/display and a fresh REPORT
   afterward. Do not infer physical low-power wake from successful registration.
4. If it hangs, stop requests. Recover manually through fastboot as needed;
   candidate85 is the matched-ECC boot-only rollback for retained logs. Keep
   raw evidence private. Original2.6 ROM restoration can overwrite the retained
   console, so collect matched-format evidence before that restoration.

The next step after awake arming passes is still Motorola PMC/request-handshake
and complete system device/CPU/cache resume integration. This image supplies
no platform sleep mode and no automatic PM wake callbacks. Deep sleep remains
unimplemented/unvalidated.
