# Motorola legacy resource profile — first isolated stage

24 October 2026. The separate `legacy-resources` profile is implemented and
builds successfully. **It enables the existing Decatf nvmap carveout allocator,
not accelerated graphics or Android startup.** At this preparation checkpoint no
candidate had been flashed. [Attempt 39 subsequently passed the initial uncached
allocator smoke test](nvmap-allocator-hardware-test.md), followed by verified
original-image restoration.

## Direct original-device observations

The restored original ROM was available over ADB. Read-only checks verified
`2.6.39.4-ElementalX-Xoom-2.1+` and `ro.product.device=wingray`, then read the
original nvmap heap sysfs metadata and `/proc/iomem`. No reboot, allocation,
device setting, filesystem write or flash was performed on the Xoom.

| Resource | Verified original-device value | New resource profile |
|---|---|---|
| Generic nvmap heap | Base `0x30000000`, size 268,435,456 bytes (256 MiB) | Same range; only enabled nvmap heap |
| fb0 | `0x2e800000–0x2effffff`, 8 MiB | Remains reserved, excluded from allocator |
| fb1 | `0x2f000000–0x2fffffff`, 16 MiB | Remains reserved, excluded from allocator |
| Original IRAM heap | Base `0x40000000`, size 262,144 bytes | **Not exposed to nvmap** |

These live observations corroborate the original Motorola source comparator's
`tegra_reserve(256 MiB, 8 MiB, 16 MiB)` layout. The comparator is the pinned
[ElementalX source](https://github.com/flar2/xoom-ElementalX/tree/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd),
not a byte-for-byte reproduction of the installed kernel binary.
Raw observations stay under ignored private artifacts.

The new kernel's SMP reset handler occupies the first KiB at `0x40000000`.
Reusing the original full IRAM heap would overlap that ownership. This stage
allocates no IRAM and enables no AVP; a later IRAM profile needs its own audit.
The values above describe the original running ROM. They do **not** prove
that nvmap has probed or allocated correctly under the candidate Linux 4.4.

## Implementation boundaries

| Change | Source identity | Scope |
|---|---|---|
| Kernel patch 0079 | `1e5a96d2` | Optional Wingray resource-only mode, incompatible with host/GART/IOMMU/CPU-frequency/AVP/media ownership; skip the downstream shared-EMC shim and exclude its DVFS object in this mode only |
| Kernel patch 0080 | `bc56d535` | Separate defconfig and DT, based on the tested two-core P3 board description |

The DT labels the **existing** `legacy-video@2e800000` reservation without
changing its range or adding overlapping reservations. Its sole nvmap entry
references that early `no-map` reservation and exposes only
`0x30000000–0x3fffffff`, with Motorola's original 32 KiB buddy size and generic
usage flag. The preceding framebuffer regions cannot be allocated by this heap.
The previous parser fixes validate the reservation and check every covered
page is absent from the ordinary ARM RAM map before creating the heap.

The profile inherits the tested USB, eMMC/BigPart, touch, GPIO, regulator,
backlight and panel properties byte-for-byte. Host1x and its DC, the panel's
driver binding, modern MC/EMC driver nodes and GART are disabled for this
experiment. All other existing child engine nodes remain disabled. The intended
display state is the firmware image, **not Android or a new scanout mode**.
This is a controlled allocator test, not a display regression test.

The expanded config excludes legacy/modern host drivers, DC/framebuffer,
GART/IOVMM, AVP/RPC/media-server, system-memory nvmap heaps, heap compaction,
page pools, DVFS, CPU scaling, suspend and hotplug. SMP/two CPUs and PL310 retain
the tested settings. No Samsung regulators, pinmux, timings or power controls
were copied.

## Dependencies found during implementation

Enabling `TEGRA_DOWNSTREAM` also defaults AVP/RPC/media support on. Those
defaults were explicitly disabled, and the resource-only mode now requires
their exclusion. The donor's shared-EMC registration also creates USB clock
lookup shims; resource-only mode skips the registration entirely, preserving
the baseline lookup path rather than introducing an unrelated dependency.

The initial link exposed an unconditional DVFS object's reference to
`tegradc_probed` when DC was excluded. Patch 0079 omits that object only in this
resource mode. Ordinary configurations retain it. The failed intermediate
build was not accepted or flashed; the corrected build passed.

nvmap heap creation still performs its existing cache maintenance. No GPU/DC
or GART driver is enabled, but this is not a claim that allocator startup has
no hardware effects or is physically validated.

## Completed checks and preserved artifacts

- Full ARM kernel link, compressed zImage and exact appended resource DTB pass.
  The original SMP2 control DTB is compiled separately for comparison.
- Existing Wingray DT sources and the SMP2 defconfig match pinned `b6483deb`.
  Compiled comparison permits only the root description, the reservation's
  new phandle, the new nvmap subtree and the six explicit disabled-node statuses.
  All original wiring/reference cells remain identical.
- The actual expanded config and symbol map confirm nvmap and exclude host,
  DC/DRM, GART and DVFS probes. A new exact release separates this profile from
  the Android-tested kernels.
- Actual Kconfig tests reject the resource-mode selection alongside host,
  RPC, GART or CPU frequency support; each conflict's parent is enabled.
- Host tests exercise the actual EMC-registration routine with resource mode
  on/off: no clock lookup/registration occurs in resource mode; the existing
  ordinary-mode path and provider error remain intact.
- Negative controls reject changed heap ranges/flags/references, IRAM/GART
  additions, changed power/pinmux/USB data, enabled engines, unsafe config,
  mismatched appended DTB and an unexpected DVFS symbol.

Private build products and checksums are preserved at
`artifacts/wingray-legacy-resources44/`, including `vmlinux`, zImage, DTBs,
resolved config, map and a source/hash manifest. The directory number identifies
an **offline compile checkpoint**, not a hardware attempt. It contains no
Android boot image or new ramdisk. The source inputs were compared against
clean kernel HEAD `bc56d535` after the build.

Reproduce without contacting a device:

```sh
XOOM_PROFILE=legacy-resources \
  XOOM_ARTIFACT_DIR="$PWD/artifacts/new-legacy-resources" \
  XOOM_BUILD_ROOT=/tmp/xoom-new-legacy-resources JOBS=4 \
  bash scripts/build-wingray.sh
python3 tests/test-wingray-resource-emc.py
python3 tests/test-wingray-legacy-resources.py \
  --dtc /tmp/xoom-new-legacy-resources/out/scripts/dtc/dtc \
  --artifacts artifacts/new-legacy-resources \
  --kconfig-build /tmp/xoom-new-legacy-resources
```

Use new artifact/build paths. The optional Kconfig test requires an idle build;
it restores the exact original config afterward.

## First physical gate, still pending

Package this kernel with the existing standalone RAM diagnostic, keeping the
Android partitions unmounted. Perform the established boot-only test with the
original image ready for restoration. A Motorola logo is expected because this
profile deliberately does not take over display.

Collect a fresh USB report and check heap registration, generic base/size,
memory exclusions, original USB/storage geometry, two CPUs, L2 and boot errors.
Then run a bounded generic-heap allocation/map/cache/pin/unpin/free smoke test
before enabling any engine or GART. Restore the original boot and verify both
original images after the test. Successful metadata alone will not establish
allocation or cache correctness.

Only after that gate should a separate profile introduce host/GART ownership,
then Motorola DC takeover and the initial RGB framebuffer compatibility path.
The matched NVIDIA userspace and offscreen rendering test remain subsequent
steps. The original ROM was left running; recovery and partition layout are
untouched.
