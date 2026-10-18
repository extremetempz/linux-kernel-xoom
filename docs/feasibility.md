# Target decision and evidence

## Recommendation

Linux 4.4 with Android 8.1 is the most defensible ambitious target found for a usable Android port. Confidence is moderate for the strategy and unproven for this Xoom. Android 6.0.1 on the legacy Xoom kernel remains the recovery baseline supplied by the owner; it must be reproduced before claiming project support. Android 7.1.2 is a useful intermediate milestone if Oreo integration stalls.

There is no defensible absolute maximum kernel or Android version from the CPU/RAM specification alone. Newer Linux is possible with sufficient board support, but a newer kernel alone does not make Android's HALs and applications work. No evidence reviewed establishes a working Android 9+ Xoom port.

| Candidate | Evidence | Decision |
|---|---|---|
| 2.6.39.4 + Android 6 | Wingray maintainer's kernel and Marshmallow device tree | Reproduction baseline |
| 3.1.10 donor | Older Decatf Samsung kernel | Possible reference; avoid an extra whole-kernel migration without a demonstrated need |
| 4.4.147 donor + Android 8.1 | Decatf Linux Makefile and Oreo manifest | Selected development target |
| 4.9 / 5.x donor branches | Preserved Decatf Linux branches, some for postmarketOS | Separate Linux experiments; no demonstrated Xoom Android advantage |

## Primary sources checked

- [Wingray Marshmallow device tree](https://github.com/Schischu/android_device_moto_wingray/tree/marshmallow-release): CPU/FPU, boot packaging, legacy HAL flags and BigPart-sized images.
- [Wingray baseline kernel](https://github.com/Schischu/android_kernel_moto_wingray/tree/jb-mr2): Makefile reports 2.6.39.4.
- [Decatf Linux 4.4 donor](https://github.com/Decatf/linux/tree/android-4.4-p4wifi): Makefile reports 4.4.147.
- [Decatf Android 8.1 manifest](https://github.com/Decatf/manifest/tree/aosp-8.1): local manifest selects a 4.4 kernel branch and modified ART, bionic, framework, HAL and arm-tcg components.
- [Older Samsung donor](https://github.com/Decatf/android_kernel_samsung_p4/tree/aosp-mm-stable): Makefile reports 3.1.10. This is a different tree from the 4.4 donor.
- [Original Xoom Oreo discussion](https://xdaforums.com/t/motorola-xoom-oreo-rom-development.3807300/): an announced effort is not proof of a functional release.

Exact commits and small original evidence files are preserved locally. The Oreo manifest uses `file:////home/r/` remotes and names absent/moved projects; it cannot be treated as a reproducible public manifest. Audit every dependency, recover forks, pin revisions and replace local remotes before a full Android sync.

## Main engineering constraints

Tegra 2 lacks NEON. The Xoom tree explicitly uses ARMv7, VFPv3-D16 and non-NEON memcpy. Preserve that throughout ART, bionic, media and native apps; an ARMv7 APK can still require NEON. Inspect donor arm-tcg/libjaunt before deciding what emulation is required.

The legacy NVIDIA graphics and multimedia stack is the largest compatibility risk. Porting display, GPU memory allocation, EGL/gralloc/HWC and codecs across the kernel ABI boundary is substantial work. Modern Tegra DRM/grate is an alternative architecture, not a binary-compatible replacement for the old Android blobs.

Xoom-specific clocks, regulators, memory reservations, eMMC, display/panel, touch, Wi-Fi, audio, charging and suspend must be established individually. Samsung board data and firmware must not be flashed onto a Xoom.

With 1 GB RAM, start with AOSP low-RAM configuration, no GApps and measured zram settings. Android 8.1 is a compatibility objective, not a promise of modern app support or present-day security maintenance. The checked 4.4.147 donor is not a current security baseline.
