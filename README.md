# Motorola Xoom MZ604 / Wingray kernel port

**DC hang candidate 85 — built, not flashed:** A separate manually armed
profile retains candidate84's ECC layout and adds process-context checkpoints
around locks, IRQ shutdown, clock/host transitions and scanout restoration.
It boots with backlight-only blanking; only explicit DCTEST arms one DC cycle.
Full ARM build and targeted offline checks pass. The DC cause remains unknown;
system suspend stays disabled. See [candidate 85](docs/dc-hang-85.md).

**Current power-management gate (28 October):** Candidate 84 passes two
same-image manual warm-reset known-probe comparisons: ECC corrected 19 then
25 console bytes, with zero unrecoverable blocks. Android boot completion
and read-only storage checks pass after both resets. This validates the
scoped corrected-console retention gate, not error-free raw retention,
DC hard-hang recovery or suspend. The corruption source and combined DC hang
remain unresolved; DC shutdown and SoC suspend stay disabled. See
[the hardware result](docs/suspend-retention-84-result.md). Candidate 84 is
currently installed; older chronological notes follow.

**Latest physical result, 26 October 2026:** Image 73k has working Wi-Fi on
Android 4.4.4 / Linux 4.4.147. The native 4.4 `bcmdhd` driver loads after
`/system` is mounted, scans 2.4 GHz networks, completes WPA2 association and
the four-way handshake, obtains a DHCP lease, survives disconnect/reconnect,
and passes Internet traffic. The display, NVIDIA GPU composition, touch, SMP,
PL310, eMMC/BigPart and USB path remain intact; screen-awake and volume-down
wake are preserved.

- **Confirmed image:** [Image 73k](artifacts/androidgpu73k-ready/wingray-android44-gpu.img)
  — 4,122,624 bytes, SHA-256 `8152ad4b5fc7c9bf30760b354bf8f6973c6c82beaeac71874f52aeaf1073f94b`
- **Recovery:** [70t](artifacts/androidgpu70t-ready/wingray-android44-gpu.img)
  and [Image 66](artifacts/androidgpu66-ready/wingray-android44-gpu.img)
- **Known limit:** station mode is deliberately limited to 2.4 GHz; 5 GHz,
  SoftAP and long suspend/resume soak testing are not part of this result.

**Bluetooth:** Image 75b pairs and connects a Sony WH-1000XM5 headset while
Wi-Fi stays connected, using an opt-in awake-only Motorola UARTC/rfkill
profile. Audio routing, microphone/SCO, suspend/reconnect and long
coexistence remain separate tests. See
[Bluetooth working image 75b](android-bluetooth-75.md). The 73k image remains
the default Wi-Fi baseline.

**Display diagnostic:** the FBTEST image proved the kernel DC path
(`Wingray display off: blank=4 dc=0`) but also showed Android was not reaching
it. The rebuilt diagnostic uses the proven sysfs blank route in the lights HAL,
with opt-in write permission. See
[FBTEST diagnostic](android-display-80-fbtest.md). It is **not flashed**.

**IRQ prerequisite:** the isolated IRQ + backlight-only profile **passed
hardware validation**: LIC parent, domain index 23, real ON events, zero
errors, no polling, and repeated backlight off/on with `dc=1`. Pstore is empty
because the ramoops DT binding lacks a memory-region. The full wakeirq failure
is narrowed to the DC/candidate-81 path. See
[IRQ result](docs/suspend-wake-82-backlight-result.md).

**Persistent storage:** Stage A read-only inspection, Stage B controlled file
test and Stage C Android persistent candidates are built. The existing
whole-disk read-only diagnostic policy is unchanged; only the new DTS-gated
profile can release p9/p10. A verified userdata backup is still required before
any write test. See [persistent storage](docs/persistent-storage-94.md). A raw userdata backup is still required; see [backup gate](docs/persistent-storage-backup.md).

**Image 93 LP2 candidate:** a separate manual-only LP2 image is built, with
Motorola PMC request/timer sequencing and the real Tegra LP2 entry path. It is
not flashed or hardware-validated; physical CPCAP wake and actual CPU/PL310/
TIMERUS restoration remain the defining first-test risks. See
[LP2 candidate](docs/lp2-candidate-93.md).

**Image 92 prerequisites:** adds reconnect-safe DPM result recovery, CPU1
hotplug and late/syscore diagnostics, with platform/LP2 entry still blocked.
Image 93 is not prepared because the PMC handshake, physical wake, CPU1 and
late/syscore gates remain unvalidated. See [Image 92](docs/device-pm-92.md).

**Device-PM stage (1 November):** Image 91 adds a full-tree devices-only DPM
test using Linux pm_test ordering, still with platform sleep blocked. Image 90
is a selected-CPCAP callback step and remains hardware-untested. Display/GPU
system restore and physical sleep wake are still blocked. See
[Image 91](docs/device-pm-91.md) and [Image 90](docs/device-pm-90-test.md).
The first DPM run exposed a missing BCM4329 SDIO keep-power capability; the
corrected image is built but not yet re-tested on hardware. The corrected
WiFi image completed devices-only DPM callbacks `result=0`; a follow-up DC
resume fix now restores the window set and first frame, pending re-test.

**Sleep status:** image 89 passes only a manual task-freezer test. Ordinary
`pm_suspend()`, device suspend, CPU sleep and deep sleep remain blocked by
design; the platform PMC parameters, device callbacks and real wake route are
still missing. See [image 89 review](docs/suspend-image89-review.md).

**Retained console:** hardware diagnostics showed `ramoops` probe failing with
`-EOVERFLOW` because the inherited size properties were one-cell u32 values.
The trace DT now uses `/bits/ 64` sizes; the corrected image is built and
offline-tested, but warm-reset retention is **not hardware-validated**. The
trace image is separate from the accepted IRQ/backlight baseline; DC and
suspend stay disabled. See
[retained-console review](docs/suspend-trace-83-review.md).

**Suspend prep isolation:** the full IRQ profile failed on hardware. A new
experimental IRQ + backlight-only profile keeps the CPCAP ON IRQ but removes
candidate 81 DC resume; it also adds a fixed pstore/previous-console snapshot.
It is built and offline-tested but not hardware-validated. See
[IRQ + backlight profile](docs/suspend-wake-82-backlight.md). Do not enable
suspend.

**Suspend prep:** the awake-only IRQ profile **failed hardware testing**:
turning the screen off lost wake and the USB diagnostic connection; a reboot
recovered it, and the failure repeated. No log was captured. Use Test 5 and do
not attempt suspend. See
[the failure record](docs/suspend-wake-82-hardware-failure.md).

**Suspend prep:** an awake-only IRQ profile is built and offline-tested:
CPCAP ON is nested through regmap/LIC with polling removed, candidate 81
display code preserved, and PM/SUSPEND still disabled. Hardware IRQ
validation is pending. See
[the suspend-prep review](docs/suspend-wake-82-review.md).

**Display power:** candidate 81 is now hardware-validated for display
off/on: native mode retained, all windows restored, flips serialized, and no
scan line. Test 5 backlight-only remains the rollback baseline. Suspend, deep
sleep and DVFS remain disabled. See
[candidate 81 result](docs/display-dc-resume-81-result.md),
[candidate 81 analysis](docs/display-dc-resume-81.md),
[Test 5](docs/display-power-80-test5-result.md) and
[DC rollback](docs/display-power-80-dc-rollback.md).

**Battery monitor:** candidate 79 passes Tests A/B/C/D at the framework
level. Disconnected: 62%, 7.64208 V, -358906 uA, ac offline. Connected:
61–62%, Charging, 7.97–8.01 V, +1.529–1.532 A, ac online. Android observed
four `isPlugged` false/true transitions without reboot and shows the real
level/voltage/current/temperature. Remaining non-blocking gaps: `health`/
`technology` properties and an explicit disconnected sysfs snapshot during
Test C. See [battery candidate 79](android-battery-79.md),
[Test A](docs/battery-79-testA.md), [Test B](docs/battery-79-testB.md),
[Test C/D](docs/battery-79-testC-D.md) and
[the detailed protocol](docs/battery-monitor-79.md). No charging controls or
battery writes are enabled.

**Power button:** Image 78 is hardware-validated. CPCAP now reports
`VERSC1=0012` / ST rev 2.2, and the back button produces press/release events;
short press toggles the screen and long press opens the power menu. The source
tree retires the volume-down `KEY_POWER` fallback and restores normal volume
keys. No rebuild was performed, so the already-flashed 78 image still carries
the old fallback mapping. See [power-button result](docs/power-key-78-result.md)
and [candidate 78](android-power-78.md). Bluetooth 75b and Wi-Fi 73k remain
stable baselines.

See [the working Wi-Fi record](docs/wifi-working.md) and the updated
[component status](STATUS.md).

**Previous GPU/touch result, 25 October 2026:** Image 63 boots Android 4.4.4
with the NVIDIA GPU composition path and a visible setup wizard on the
internal LCD. The DC scans out a GPU-composed 1280x800 framebuffer and the
LP8550 backlight is on. Image 64 confirms working touch: 25 presses, 22
releases, 840 position events and three simultaneous contacts in one verified
report. HWC overlay composition is not yet exercised (`numHwLayers=0`). See
[Image 63 result](android-gpu-63-result.md) and
[Image 64 touch result](android-gpu-64-touch-result.md); original
boot/recovery restoration is pending after these tests.

**Earlier SMP result, 24 October 2026:** Images 37/38 boot Android 4.4.4 on
Linux 4.4.147 with both Tegra 2 CPUs online and PL310 enabled. Attempt 38
uses the unchanged non-trace image from attempt 36. Two fresh reports,
a bounded two-core memory/affinity check, advancing local timers/reschedule IPIs
and image-37 CPU1 startup checkpoints confirm initial SMP execution. Both
original image hashes match after restoration. Earlier images demonstrated
Welcome and touch, USB and full-capacity/all-ten BigPart storage.

See the [six-component completion status](STATUS.md),
[non-trace attempt-38 evidence](docs/trace-boot-attempt-38.md),
[image-37 hardware evidence](docs/trace-boot-attempt-37.md) and
[diagnostic implementation](docs/smp-startup-trace-37.md).
Broader boot repeatability and cache/stress testing are still pending;
the cause of image 36's failure remains unknown. DVFS and accelerated NVIDIA
graphics remain disabled. This remains an experimental RAM-data/software-
graphics boot; a lockscreen, suspend and full ROM functionality are unverified.

The [Decatf reuse audit and staged patch plan](docs/decatf-reuse-plan.md) compares SMP, PL310, DVFS, NVIDIA graphics and Android IPC against the original working stack. It preserves the hardware-tested configurations.

Kernel bring-up workspace, prepared 18 October 2026.

See the [early-boot review](docs/early-boot-review.md) for the failed physical
boot analysis, verified image layout, unresolved hypotheses and staged plan.

**Original engineering target: Linux 4.4 + AOSP Android 8.1, ARMv7 without NEON, with Xoom BigPart.** The delivered and hardware-tested build is the Android 4.4.4 Image 73k above. The first experimental Linux 4.4.147 Wingray kernel and appended DTB compile. The first physical diagnostic boot stayed at the Motorola logo; later images reached Android 4.4.4 Welcome with working touch. This remains an experimental port, with software graphics and RAM-backed data, rather than a complete newer ROM.

Decatf's Galaxy Tab 10.1 Linux donor is genuinely 4.4.147. Its Oreo manifest selects the 4.4 kernel family. The original Wingray baseline is 2.6.39.4. Same SoC does not imply interchangeable boot images or peripheral drivers.

Start with [kernel status and build instructions](kernel/README.md), [feasibility](docs/feasibility.md), [BigPart](docs/bigpart.md), and [bring-up milestones](docs/bringup.md). Exact upstream revisions are in `sources.lock.json`; downloaded source is excluded from this repository, and all kernel changes are preserved as a reproducible patch series under `kernel/patches`.

```sh
python3 scripts/fetch-sources.py
python3 scripts/apply-kernel-patches.py
bash scripts/setup-toolchain.sh
bash scripts/test-bigpart.sh
bash scripts/build-wingray.sh
```

The new target is `wingray_bringup_defconfig` with `tegra20-motorola-wingray.dts`. It separates Samsung-only initialization, enables eMMC, GPIO keys, UART, USB gadget serial and persistent logging, preserves boot memory, and scopes BigPart remapping to the Xoom eMMC controller. A second patch adds P3/AUO display, touch, BCM4329 wiring, CPCAP/MAX8649 rails and restart support. These drivers are not yet runtime validated; suspend, charging and other peripherals remain unfinished. See [hardware validation](docs/hardware-validation.md). The next gates include RAM-only setup/provisioning toward the lockscreen, independently instrumented CPU/cache controls, Motorola power sequencing and legacy graphics compatibility. Unrelated peripherals remain deferred.

GitHub destination: `extremetempz/linux-kernel-xoom`. Repository visibility was changed to private on 18 October 2026.

Upstream source and evidence retain their original licenses. Keep kernel copyright notices and GPL obligations when distributing kernel binaries; private hosting does not change those obligations.


The earlier `SYSCTEST result=0` is invalid as syscore evidence: freeze suspend
returns before syscore in this tree. Image 92c corrects the diagnostic to
`PM_SUSPEND_MEM`/`TEST_CORE` with a dummy platform enter; that corrected path is
not yet hardware-tested.
