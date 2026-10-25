# Motorola Xoom MZ604 / Wingray kernel port

**Latest physical result, 25 October 2026:** Image 63 boots Android 4.4.4
with the NVIDIA GPU composition path and a visible setup wizard on the
internal LCD. The DC scans out a GPU-composed 1280x800 framebuffer and the
LP8550 backlight is on. HWC overlay composition is not yet exercised
(`numHwLayers=0`). See [Image 63 result](android-gpu-63-result.md);
original boot/recovery restoration is pending after this test.

**Latest physical result, 24 October 2026:** Images 37/38 boot Android 4.4.4 on
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

**Selected engineering target: Linux 4.4 + AOSP Android 8.1, ARMv7 without NEON, with Xoom BigPart.** The first experimental Linux 4.4.147 Wingray kernel and appended DTB compile. The first physical diagnostic boot stayed at the Motorola logo; later images reached Android 4.4.4 Welcome with working touch. This remains an experimental port, with software graphics and RAM-backed data, rather than a complete newer ROM.

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
