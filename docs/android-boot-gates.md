# Android startup gates after early-memory repair

Updated 22 October 2026 against the checked-out Wingray device tree and the
working ROM's captured kernel configuration. Physical results are identified below; other
items remain source/configuration findings, not hardware validation.

1. Complete memory setup without descriptor-array overrun. Candidate 14 passed
   the lowmem-ceiling correction. Keep the retained firmware/video
   reservations and BigPart geometry unchanged.
2. Reach kernel initcalls and execute an isolated RAM diagnostic. Enable only
   the required USB controller/PHY, board data-switch GPIOs and serial gadget
   first. Candidate 23 enumerates USB and delivers a diagnostic report; image 24
   passed two fresh checksummed reports across close/reopen. Keep that
   observation path for additional probes. Restore the original
   boot image and verify boot/recovery after every failed diagnostic.
3. Enable eMMC and the Xoom-only BigPart view. Read controller/partition
   geometry without mounting Android partitions. Compare every named partition
   against the existing layout before attempting Android init. Image 24 matched
   all ten extents but reported 4 MiB less whole-disk capacity. Image 25 verified
   the scoped capacity fix and exposed a masked GPT-option parser defect.
   Image 26 corrected parsing and physically passed full-capacity/all-ten-extents
   comparison twice. This passes discovery/geometry, not filesystem integrity
   or storage stress validation.
4. Match the installed Android userspace. Its kernel enables Binder, ashmem,
   cgroups, Android logging and legacy NVIDIA interfaces. The current minimal
   trace profile deliberately omits most of these. Binder's old 32-bit API is
   required for Android 4.4 and earlier; it must be disabled for the newer API
   used by Oreo. Preserve distinct configurations instead of silently changing
   the installed-ROM ABI while developing the future ROM.
5. Adapt the RAM-disk device paths to this kernel. The Wingray device fstab
   names `/dev/block/platform/sdhci-tegra.3/by-name/...`; a DT SDHCI driver can
   expose a different platform path. Android init requires correct read-only
   system and writable data/cache mounts. Do not change on-disk partitions to
   compensate for a userspace device-path mismatch.
6. Validate display/input and graphics userspace compatibility. Image 27 passed
   the shared panel-supply/I2C dependency test and read the LP8550 identity and
   twelve registers twice. Image29 subsequently passed P3 current control, a real 1280×800 framebuffer and operator-confirmed visible RGB scanout while retaining USB/storage. Touch and Android graphics/framework remain unvalidated. The legacy
   init/ueventd rules expect `/dev/nvmap` and `/dev/nvhost-*`. The current
   Wingray DRM configuration does not provide those legacy ioctl interfaces.
   Successful eMMC and Binder initialization therefore does not establish that
   the installed hardware compositor/EGL stack can display Android. Reconcile
   the donor NVIDIA ABI or use a compatible userspace graphics path; validate
   the panel, backlight and touch separately.
7. Only then test Android init, service startup, framework and UI, keeping
   boot logs and restoration evidence. Wi-Fi, audio, charging and suspend
   validation follow their actual drivers and board power sequencing.

The diagnostic RAM disk mounts only virtual filesystems. It is intentionally
separate from installed Android init, so an early diagnostic success must not
be described as a working Android ROM.

Relevant checked-in sources: `sources/device-wingray/fstab.stingray`,
`rootdir/init.stingray.rc`, `rootdir/ueventd.stingray.rc`, and the donor
`drivers/android/Kconfig`. Downloaded sources are pinned by `sources.lock.json`.
