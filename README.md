# Motorola Xoom MZ604 / Wingray kernel port

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

**Power button:** candidate 76 (CPCAP CS + native32) caused significant
screen flicker and is rejected. Candidate 76a isolates the native32 framing
while restoring the previously stable CS polarity; it is built and tested but
**not hardware validated**. Do not flash 76. See
[the rejected 76 analysis](android-power-76.md) and
[76a isolation candidate](android-power-76a.md). Bluetooth 75b and Wi-Fi 73k
remain the working recovery baselines.

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
