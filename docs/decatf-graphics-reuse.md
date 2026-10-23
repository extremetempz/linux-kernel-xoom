# Decatf graphics reuse audit

23 October 2026. Read-only source and ABI review, performed after image 32
reached the Android Welcome screen and the operator confirmed touch response.
This audit changes no kernel, device tree, boot image or hardware setting.

## Recommendation and evidence limits

Reuse Decatf's existing NVIDIA implementations as the first reference for a
**separate legacy-graphics experiment**. Do not replace the working image-32
DRM framebuffer/software-graphics configuration. Its visible Android boot is
already established; accelerated graphics is an additional milestone.

The strongest compatibility issue found is concrete: the original Wingray
source lineage uses a **24-byte nvhost write-submission header**, while the
Decatf staging driver consumes **16 bytes**. Matching device names and the
shared ioctl numbers does not resolve that difference. The installed NVIDIA
blob's actual submission dialect must be measured before enabling it.

Evidence labels below mean:

- **Verified source/ABI:** inspected pinned source, expanded configuration or
  compiled 32-bit header layouts. This does not establish hardware behavior.
- **Verified artifact:** metadata from the owner's preserved working ROM.
- **Hypothesis/gate:** a proposed adaptation or test, not a proven compatible
  implementation.

The running baseline is `2.6.39.4-ElementalX-Xoom-2.1+` with Android 4.4.4.
Its saved embedded configuration and saved HAL ELF files are direct evidence.
Schischu's `jb-mr2` and flar2's ElementalX trees are source comparators; neither
has been reproduced byte-for-byte as that installed binary. Do not describe
Schischu's source alone as the exact working-ROM kernel.

## Pinned primary sources

Public refs were resolved with read-only Git queries on 23 October 2026. Local
checkouts/metadata were inspected at the revisions below; the GitHub web
fetcher could not render several commit pages, so those pages were read
through Git/raw/API instead. No vendor binaries were downloaded in this audit.

| Repository/reference | Revision inspected | Purpose |
|---|---|---|
| [Decatf/linux, android-4.4-p4wifi](https://github.com/Decatf/linux/tree/bbcece6d21c83b6280061a91d27566aff1951c94) | `bbcece6d21c83b6280061a91d27566aff1951c94` | Existing Linux 4.4.147 donor, including staging NVIDIA drivers |
| [Decatf common device, android-4.4](https://github.com/Decatf/android_device_samsung_p4-common/tree/05a8f4927f7f16d79b6c74fba4be877323db04a6) | `05a8f4927f7f16d79b6c74fba4be877323db04a6` | KitKat legacy graphics build choices |
| [Decatf common device, aosp-8.1-dev](https://github.com/Decatf/android_device_samsung_p4-common/tree/1ffdea960852f8a9c50133f7849cbc83d84f8ae4) | `1ffdea960852f8a9c50133f7849cbc83d84f8ae4` | HWC wrapper, linker shims, EGL selection |
| [Decatf p4wifi, aosp-oreo](https://github.com/Decatf/android_device_samsung_p4wifi/tree/483f6d877f1186489af17ea80c89cf7c43c9f431) | `483f6d877f1186489af17ea80c89cf7c43c9f431` | Product and proprietary-file declarations |
| [Decatf vendor metadata, aosp-8.1](https://github.com/Decatf/android_vendor_samsung_p4wifi/tree/08201abb058a96a1a626cb397b6cdbac43f78876) | `08201abb058a96a1a626cb397b6cdbac43f78876` | File names/sizes, build and loader metadata only |
| [Schischu Wingray kernel, jb-mr2](https://github.com/Schischu/android_kernel_moto_wingray/tree/6b3d70fff905b7395fd15992c3779b27d1b6c101) | `6b3d70fff905b7395fd15992c3779b27d1b6c101` | Original 2.6.39.4 ABI lineage |
| [flar2 Xoom ElementalX](https://github.com/flar2/xoom-ElementalX/tree/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd) | `3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd` | Closer named baseline source comparator |
| [Wingray device, marshmallow-release](https://github.com/Schischu/android_device_moto_wingray/tree/057937ecd971591397b6a38030b8f8a9ae138da0) | `057937ecd971591397b6a38030b8f8a9ae138da0` | Existing Motorola HWC wrapper/reference flags; not the installed KitKat build |

The existing [Oreo manifest](https://github.com/Decatf/manifest/blob/86da0eca29258e6fa7e891cb887069cb577f9bba/local_manifest.xml)
contains local `file:////home/r/` projects. A matching public branch does not
prove it equals the maintainer's former local checkout. A full reproducible
Oreo userspace manifest remains a separate prerequisite.

## Component classifications

| Component | Classification | Reason and next gate |
|---|---|---|
| Generic nvmap allocator and shared 32-bit ioctl declarations | **Reusable with Motorola-specific modifications** | Already present in the donor; 13 common ioctl encodings and seven argument sizes match both Wingray comparators. Carveouts, mapping/cache behavior, GART ownership and lifecycle still need Motorola validation. |
| Generic nvhost engines, channel/syncpoint machinery | **Reusable with Motorola-specific modifications** | Already ported to this donor kernel, but original write-submission layout differs. Validate the installed blob protocol, memory manager and clock/reset integration before any submission. |
| Current DRM/GEM interface as a substitute for NVIDIA nvmap/nvhost | **Incompatible** | Different device/interface, object handles and submission API. A common host1x engine does not translate userspace ABI. |
| Existing software EGL/default gralloc control | **Directly reusable** | Already used for the physical Android boot, including image 32. Keep it as the rollback/control path. |
| Decatf open-source HWC v0-to-v1 wrapper | **Reusable with Motorola-specific modifications** | Useful existing implementation, also present in the Wingray device lineage. Requires the correct original Motorola HAL, matching Android private APIs and a working legacy kernel graphics path. |
| Decatf `libdgv1` loader shim | **Reusable with Motorola-specific modifications**, if needed | Reusable path-fixing source, but its vendor path and required ELF symbol changes are specific to the selected blob set/Android linker. KitKat control does not currently need it. |
| Decatf proprietary EGL/gralloc/HWC binary set as a direct Wingray replacement | **Incompatible as a drop-in** | No demonstrated matching ABI/dependency set; public metadata differs from the installed libraries. Any later experiment needs its own audited, legally usable matched set. |
| Samsung display/carveout/power tables and Samsung HWC workaround | **Incompatible as a Wingray import** | Board-specific values are not validated for Xoom. Preserve Motorola wiring, panel timings, reservations and power sequencing. |

“Reusable with modifications” is a source-reuse recommendation, not a claim
that enabling its configuration symbols will work.

## Kernel graphics comparison

**Verified configuration.** The original working-ROM configuration enables
`TEGRA_GRHOST`, `TEGRA_DC`, `FB_TEGRA` and `TEGRA_NVMAP`. It also enables nvmap
reclaim/highmem/carveout-killer options. Image 32 instead enables `TEGRA_HOST1X`,
`DRM_TEGRA` and DRM fbdev, with `DRM_TEGRA_STAGING` and `TEGRA_DOWNSTREAM` off.
The expanded image-32 configuration SHA-256 is
`ce92df8d4e7e18bc727eb8e8130bf6d9a3a977814c55e28dda7b9c3ae1cf91b1`.

The donor retains a complete alternative under `drivers/staging/tegra/video/`:
nvmap, host1x/nvhost, GR2D/GR3D, DC and framebuffer support. These files are
unchanged by the current Wingray patch series. Its
[Kconfig](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/tegra/video/Kconfig)
excludes `TEGRA_GRHOST` and `TEGRA_NVMAP` when `TEGRA_HOST1X` is selected. Do not
bypass that exclusion and bind two drivers to the same engines or DC.

The current
[DRM API](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/include/uapi/drm/tegra_drm.h)
uses GEM handles, DRM channel contexts, command buffers and DRM syncpoint
ioctls. The legacy NVIDIA libraries expect nvmap handles, nvhost channels and
NVIDIA display controls. A device-node alias would not bridge these APIs.

**Verified 32-bit layout check.** Actual declarations were extracted from the
three pinned kernel trees and the current committed Wingray tree, compiled
with the project's ARM GCC 4.9 using ARMv7-A/softfp/VFPv3-D16, and constants
read from the object file. `unsigned
long` and pointers are therefore ARM32 widths, not the host's 64-bit widths.
This checks encoding/layout only, not allocation or execution semantics.

Reproduce the measurement with the local sources/toolchain already present:

```sh
python3 scripts/audit-tegra-graphics-abi.py --save-dir artifacts/new-graphics-abi-audit
```

Use a fresh evidence directory. The tool fetches nothing, runs no generated
code, touches no device and changes no kernel configuration. It reads committed
headers, uses each revision's own ARM ioctl encoding selection, records source
commits/header hashes/compiler details and bounds its JSON report to 64 KiB.
An exit status of zero means the measurement completed; its compatibility
verdict remains `not_established`. Uncommitted source edits are not measured.
The checked run is saved privately under `artifacts/decatf-graphics-audit/`,
including generated C, ARM relocatable objects and the initial comparison.

| nvmap operation | ARM32 ioctl encoding, identical in all four source snapshots |
|---|---|
| CREATE / CLAIM / FROM_ID | `c0084e00` / `c0084e01` / `c0084e02` |
| ALLOC / FREE / MMAP | `40104e03` / `00004e04` / `c0144e05` |
| WRITE / READ / PARAM | `401c4e06` / `401c4e07` / `c00c4e08` |
| PIN_MULT / UNPIN_MULT / CACHE / GET_ID | `c00c4e0a` / `400c4e0b` / `40104e0c` / `c0084e0d` |

The corresponding create/alloc/map/rw/pin/param/cache structures occupy
8/16/20/28/12/12/16 bytes. Sources:
[original declaration](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/drivers/video/tegra/nvmap/nvmap_ioctl.h),
[donor declaration](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/tegra/video/nvmap/nvmap_ioctl.h).
Shared heap flags also agree for system memory, IOVMM, IRAM and generic
carveout; the donor adds VPR and a zeroed-pages flag. Equal constants do not
prove equal memory lifetime, cache maintenance, sharing or security behavior.

| nvhost field/API | Wingray source comparators | Decatf staging |
|---|---|---|
| `nvhost_submit_hdr`, consumed by `write()` | 24 bytes; includes `num_waitchks`, `waitchk_mask` | 16 bytes; four leading fields only |
| Extended submit | Not defined in these comparators | 48-byte header, versioned `SUBMIT_EXT` |
| Common channel ioctl numbers 1–5 | Match | Match |
| Common control ioctl numbers 1–5 | Match | Match |
| Additional timed wait/version operations | Absent in these headers | `WAITEX`, `WAITMEX`, `GET_VERSION`, `READ_MAX` |

Sources: [Wingray header](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/arch/arm/mach-tegra/include/mach/nvhost.h),
[donor header](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/tegra/include/linux/nvhost_ioctl.h),
[donor parser](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/tegra/video/host/bus_client.c).
The parser explicitly copies `sizeof(struct nvhost_submit_hdr)` before
processing command buffers. Sending the older six-word stream unchanged can
shift subsequent fields. **Unknown:** which paths the installed
`libnvrm_channel.so` actually uses; it has not been traced in this audit.

The
[Samsung DT](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/boot/dts/tegra20-samsung_p3.dts)
illustrates how Decatf supplies nvmap carveouts, legacy host binding and DC
resources. Its generic carveout is `0x30000000`/256 MiB and it includes Samsung
CMC623 panel choices. Those addresses, timings and EMC assumptions must not be
copied over the Wingray reservations or its working AUO/LP8550 path. The donor's
shared-EMC clock shim can change EMC rate; classify it as a dependency requiring
the separate Motorola power/memory audit, not harmless graphics glue.

## EGL, gralloc and composer comparison

**Verified artifacts.** The owner's installed gralloc is 295,388 bytes and
depends on `libnvos`, `libnvrm`, `libnvrm_channel`, `libnvddk_2d_v2`, `libpkip`
and `libcrypto`, as well as Android runtime libraries. Its dynamic section also
contains `DT_TEXTREL`/`FLAGS TEXTREL`; a newer Android linker's text-relocation
policy must be checked explicitly. Its HWC is 13,964 bytes
and also depends on NVIDIA RM/channel/2D libraries. Saved ELF attributes show
ARMv7, gralloc tagged VFPv3 and HWC tagged VFPv3-D16. Attributes are not a full
instruction audit and do not certify every transitive dependency as non-NEON.

Private provenance hashes (no binaries are committed): gralloc
`fdc83469e64e70c080452259f24d452529f12a9b20cc8054c2f5e069c4c271ad`;
HWC `5541222fa0f93320ea1976a1c959b02811f4a9881eba1d47f0fd1d18ffc76823`.
The public vendor tree declares a 299,032-byte gralloc and an 18,108-byte
`hwcomposer.tegra_v0.so`. These are not identical files to the installed pair.
Their compatible dependencies cannot be inferred from their names. See the
[pinned vendor tree](https://github.com/Decatf/android_vendor_samsung_p4wifi/tree/08201abb058a96a1a626cb397b6cdbac43f78876/proprietary/vendor/lib).

Decatf's
[KitKat board settings](https://github.com/Decatf/android_device_samsung_p4-common/blob/05a8f4927f7f16d79b6c74fba4be877323db04a6/BoardConfigCommon.mk)
select the old HWC API, legacy framebuffer EGL, ARMv7-A/VFPv3-D16 and non-NEON
memcpy. These are useful compatibility references. The newer
[board settings](https://github.com/Decatf/android_device_samsung_p4-common/blob/1ffdea960852f8a9c50133f7849cbc83d84f8ae4/BoardConfigCommon.mk)
select 32-bit SurfaceFlinger, Tegra2 HWC integration and screenshot/dequeue
workarounds. None is a kernel ABI adapter or proof of a reproducible Oreo ROM.

The open-source
[HWC wrapper](https://github.com/Decatf/android_device_samsung_p4-common/blob/1ffdea960852f8a9c50133f7849cbc83d84f8ae4/hwc/hwc_tegra2.cpp)
loads an original `hwcomposer.tegra_v0.so`, translates layer lists, and tries
NVIDIA VBLANK syncpoints before timer fallback. It requests `tegra_dc0` or
`tegra_dc_0` and `nvhost-ctrl`; these do not exist on the present DRM path. It
advertises HWC 1.0 and closes acquire-fence descriptors without waiting in that
routine, returning release fences as `-1`. Its synchronous assumptions require
review against the selected HAL/framework. A preparation-buffer call also
passes the set-buffer size to `ensure_xlatebuf`; audit/fix this independently
before reuse. Do not enable the optional Samsung crop workaround for Motorola.

There is already a related
[Wingray wrapper](https://github.com/Schischu/android_device_moto_wingray/blob/057937ecd971591397b6a38030b8f8a9ae138da0/hwc/hwc_tegra2.cpp)
in the local device lineage. Diff it before importing another implementation.
This is reusable existing code, not a reason to write a new composer.

Decatf's
[loader shim](https://github.com/Decatf/android_device_samsung_p4-common/blob/1ffdea960852f8a9c50133f7849cbc83d84f8ae4/libdgv1/libdgv1.c)
tries an absolute vendor path after `NvOsLibraryLoad` fails. The
[associated README](https://github.com/Decatf/android_vendor_samsung_p4wifi/blob/08201abb058a96a1a626cb397b6cdbac43f78876/proprietary/vendor/lib/egl/README)
describes binary-specific edits. Never apply its literal offsets to different
Motorola files. For a newer Android linker, first inventory undefined symbols,
private `libgui`/`libutils` APIs, namespace rules, ELF class and softfp calling
convention. Test the actual dependency closure on a non-NEON target. The
repository's Apache-licensed build files do not grant redistribution rights to
the proprietary libraries they name.

## Separate patch and validation sequence

These are proposed work units, **not patches already applied**. Each gets an
independent source commit and fresh artifact; stop at a failed gate. Preserve
the image-32 defconfig, DTB, software overlays, USB report protocol and original
boot/recovery backups throughout.

| Order / patch boundary | Offline gate | Physical gate before proceeding |
|---|---|---|
| G0: graphics ABI inventory/test fixtures only | Reproduce ARM32 ioctl/structure/offset tables from pinned headers; inventory owner's full NVIDIA dependency closure and selected blob submission dialect; no blob redistribution | Read-only observation of the original working stack if a missing ABI fact requires it |
| G1: isolated legacy-graphics profile and dependency separation | No edits to tested profile; resolve exclusive host/DC ownership and staging clock/MC/GART dependencies; expanded-config and DT resource/overlap checks; full ARM link, no unresolved symbols | None until resource ownership is unambiguous; retaining current DRM or switching to legacy DC must be an explicit design choice |
| G2: Motorola nvmap memory integration | Reuse allocator, add only validated Wingray memory resources; keep every existing reservation; test range/overflow/refcount/mmap/error paths and cache-policy calls | Tiny bounded allocate/map/share/free tests, zero-filled data, stable available RAM, no USB/storage/touch regression; no graphics submission yet |
| G3: nvhost ABI adaptation, separate from board resources | Preserve measured old submission dialect or select a proven matched library set; exercise malformed stream/relocation/wait-count rejection and timeout cleanup | Safe metadata first, then one bounded 2D/3D operation; verify syncpoint advancement, timeout/recovery, data result and absence of corruption |
| G4: legacy display interface, only if required | Translate Motorola timings/power/backlight data, never Samsung tables; one DC owner; verify framebuffer strides, formats and bounds | Color/stride patterns and original 1280×800 scanout; preserve touch, USB and BigPart report checks |
| G5: selected Motorola EGL/gralloc in a RAM-only test overlay | Resolve every ELF dependency/undefined symbol; prove ARMv7/non-NEON compatibility; run allocation/lock/unlock and EGL configuration tests outside the system compositor first | Correct rendered image/readback and repeated allocation/free without leaks or hangs |
| G6: existing HWC wrapper adaptations as a separate userspace patch | Fix buffer-capacity bookkeeping; test layer translation and fence ownership/ordering; match actual Android/HAL version; no Samsung workaround | Stable Welcome/lockscreen, repeated input/redraw, rotation and screen on/off only after power sequencing is independently validated; logs show actual accelerated path |

Every physical experiment retains boot-partition-only testing, original-image
restoration and complete boot/recovery readback verification. No recovery,
partition layout, original userdata/cache or proprietary ROM publication is
part of this audit. An accelerated screenshot or a successful library load
alone is insufficient to pass rendering, synchronization or stability gates.

## Subsequent development checkpoint

See [power, graphics and ABI implementation](power-graphics-abi-stage.md) for
separate nvhost, EMC, voltage-unit, frequency-policy and composer corrections,
expanded ashmem checks, ARM build evidence and remaining hardware gates.
The earlier audit describes its pinned review snapshot.
