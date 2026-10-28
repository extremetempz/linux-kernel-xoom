# Candidate88 — awake parent wake-reference test passes

28 October 2026. Tested the exact [prepared Android image](wake-arm-88-prepared.md):
4,214,784 bytes, SHA-256
`f5eca1470eb34d26ea163d82259152e4a26e11870b35e834077485e0beacd570`.
**Awake IRQ wake registration passes. Physical wake from sleep was not tested.**

## Deployment and settling interval

The operator authorized boot-only flash and requested a two-minute wait before
testing. Fastboot identified Xoom Wi-Fi and confirmed transfer, boot write and
reboot. Original boot/recovery backup files passed their recorded SHA-256
checks. Recovery and partition layout were untouched; no live partition
readback is claimed. The requested two-minute interval elapsed before the
baseline REPORT or WAKETEST was sent. The operator renewed temporary serial
access after USB enumeration.

Candidate88 remains installed. Candidate85 and both original backup images
remain preserved locally; no rollback/original restoration followed this test.

## Baseline

A fresh nonce/hash-verified REPORT confirmed `sys.boot_completed=1`,
SurfaceFlinger/zygote operation, CPUs0–1 and matching full eMMC/ten-BigPart
geometry under the RAM-data/read-only-system policy. SurfaceFlinger reported
`GLES: NVIDIA Corporation, NVIDIA Tegra, OpenGL ES 2.0`. This is compositor
identity, not a new GPU correctness/stress test.

The kernel logged `Wingray PM preparation: system sleep entry blocked`.
CPCAP used the LIC parent, normal ON domain23, polling0 and errors0. Parent
and nested Linux IRQ numbers were discovered dynamically. A startup
sysfs-group warning at0.767770 seconds was already present in this baseline
and remained in later reports; no claim of warning-free boot is made.

## One WAKETEST

The fixed request returned a complete verified 561-byte payload, SHA-256
`6087d347545825afe1c755da625dd47c60444f4c3687096680bac788ba551452`.
The relevant state sequence was:

```text
WAKETEST_BEFORE owned=0 parent_wake=0 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked
WAKETEST_ARM_RC 0
WAKETEST_ARMED owned=1 parent_wake=1 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked
WAKETEST_DISARM_RC 0
WAKETEST_AFTER owned=0 parent_wake=0 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked
WAKETEST_PROCESS_RC 0
```

The host recorded `wake_arm_commands_completed=true` and
`physical_wake_validated=false`. The driver acquired and released its one
parent reference successfully, and the parent IRQ-core wake flag was clear
at exit. No error rollback or cleanup retry was needed. No sleep-state write,
DC cycle, GPIO/PMIC-control write or voltage change was requested by this test.

A fresh post-test REPORT again passed integrity, Android boot completion and
storage checks. A separate PSTORE snapshot confirmed the ECC16 backend at the
unchanged reserved region with matching record/console/pmsg sizes. This was
a same-boot snapshot, not a new hard-hang/retention comparison.

## Physical key/display/touch follow-up

The operator was asked to power the screen off/on, check full darkness,
restoration without a scan line and continued touch. The response was
“all good!”. The final REPORT again passed integrity and storage geometry;
Android boot completion and NVIDIA GLES identity remained present. CPCAP
recorded16 ON IRQ events, polling0 and errors0. This count does not imply
exactly one operator button cycle. Backlight logs show successful off/on
with DC retained at1, as intended for this profile.

The report contains Android Awake and Asleep policy snapshots at different
times. Android's display/sleep policy is not evidence of SoC suspension:
system entry remained blocked. No Wi-Fi reconnect, Bluetooth pairing,
peripheral stress, power-consumption or actual low-power wake test occurred.

## Accepted result and next gate

**One checked parent wake-reference arm/disarm pair passes on hardware,
followed by working physical power-button/display/touch operation.** This
validates the awake IRQ-core/LIC registration path and balanced ownership.
It does not establish PMC electrical wake routing, CPU power-gating wake,
DRAM retention, system-PM device resume or reliable low-power operation.
The test reference is cleared; nothing was left intentionally armed.

Next development remains Motorola PMC/request-handshake configuration and
system device/CPU/cache suspend-resume integration, followed by a separately
reviewed controlled low-power profile. Keep the preparation sleep-entry
block until those dependencies are addressed. LP0/LP1, Android autosuspend
and measured deep-sleep savings remain unimplemented/unvalidated.

Private captures: `artifacts/wakearm88-baseline`, `wakearm88-cycle1`,
`wakearm88-after-cycle1`, `wakearm88-pstore-after-cycle1`,
`wakearm88-after-keycheck` and `wakearm88-deployment`. Saved frame/payload
lengths and hashes were checked; raw reports, identifiers and ROM contents
are not uploaded. No failed physical low-power recovery path was exercised.
