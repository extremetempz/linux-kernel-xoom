# Motorola Xoom MZ604 / Wingray kernel port

**Latest physical result, 22 October 2026:** Image 31 boots the installed Android
4.4.4 userspace on Linux 4.4.147 and displays the real Welcome screen. Two fresh
verified USB reports show both boot-completion flags set, SystemUI running and
retained full-capacity/all-ten BigPart geometry under the read-only/RAM-data
policy. Original boot and recovery are completely verified after restoration.
Touch is deliberately disabled in this profile, and a lockscreen is not yet
verified. See the [image-31 result](docs/trace-boot-attempt-31.md), the
[image-30 failure and diagnosis](docs/trace-boot-attempt-30.md) and
[Android gates](docs/android-boot-gates.md).

Kernel bring-up workspace, prepared 18 October 2026.

See the [early-boot review](docs/early-boot-review.md) for the failed physical
boot analysis, verified image layout, unresolved hypotheses and staged plan.

**Selected engineering target: Linux 4.4 + AOSP Android 8.1, ARMv7 without NEON, with Xoom BigPart.** The first experimental Linux 4.4.147 Wingray kernel and appended DTB compile. The first physical diagnostic boot stayed at the Motorola logo with no USB serial output; this is not a completed port or a working Xoom ROM.

Decatf's Galaxy Tab 10.1 Linux donor is genuinely 4.4.147. Its Oreo manifest selects the 4.4 kernel family. The original Wingray baseline is 2.6.39.4. Same SoC does not imply interchangeable boot images or peripheral drivers.

Start with [kernel status and build instructions](kernel/README.md), [feasibility](docs/feasibility.md), [BigPart](docs/bigpart.md), and [bring-up milestones](docs/bringup.md). Exact upstream revisions are in `sources.lock.json`; downloaded source is excluded from this repository, and all kernel changes are preserved as a reproducible patch series under `kernel/patches`.

```sh
python3 scripts/fetch-sources.py
python3 scripts/apply-kernel-patches.py
bash scripts/setup-toolchain.sh
bash scripts/test-bigpart.sh
bash scripts/build-wingray.sh
```

The new target is `wingray_bringup_defconfig` with `tegra20-motorola-wingray.dts`. It separates Samsung-only initialization, enables eMMC, GPIO keys, UART, USB gadget serial and persistent logging, preserves boot memory, and scopes BigPart remapping to the Xoom eMMC controller. A second patch adds P3/AUO display, touch, BCM4329 wiring, CPCAP/MAX8649 rails and restart support. These drivers are not yet runtime validated; suspend, charging and other peripherals remain unfinished. See [hardware validation](docs/hardware-validation.md). The next gate is an isolated real-touch profile and RAM-only setup/provisioning toward the lockscreen; unrelated peripherals remain deferred.

GitHub destination: `extremetempz/linux-kernel-xoom`. Repository visibility was changed to private on 18 October 2026.

Upstream source and evidence retain their original licenses. Keep kernel copyright notices and GPL obligations when distributing kernel binaries; private hosting does not change those obligations.
