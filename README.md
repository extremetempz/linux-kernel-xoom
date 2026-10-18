# Motorola Xoom MZ604 / Wingray kernel port

Research and bring-up workspace, prepared 18 October 2026.

**Selected engineering target: Linux 4.4 + AOSP Android 8.1, ARMv7 without NEON, with Xoom BigPart.** This is a porting target, not a working Xoom ROM. No kernel has been compiled or booted by this project yet.

Decatf's Galaxy Tab 10.1 Linux donor is genuinely 4.4.147. Its Oreo manifest selects the 4.4 kernel family. The original Wingray baseline is 2.6.39.4. Same SoC does not imply interchangeable boot images or peripheral drivers.

Start with [feasibility](docs/feasibility.md), [BigPart](docs/bigpart.md), and [bring-up milestones](docs/bringup.md). Exact upstream revisions are in `sources.lock.json`; downloaded source is excluded from this orchestration repository.

```sh
python3 scripts/fetch-sources.py
# After installing a compatible ARM cross-toolchain:
CROSS_COMPILE=/absolute/path/to/arm-eabi- bash scripts/build-baseline.sh
```

The donor is intentionally not given a Xoom build target: a Samsung defconfig cannot produce a validated Xoom image. First reproduce and boot the baseline, then develop Xoom support on the donor in its own Git repository.

GitHub destination: `extremetempz/linux-kernel-xoom`. Repository visibility was changed to private on 18 October 2026.

Upstream source and evidence retain their original licenses. Keep kernel copyright notices and GPL obligations when distributing kernel binaries; private hosting does not change those obligations.
