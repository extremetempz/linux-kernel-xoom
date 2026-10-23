# Decatf Android IPC, logging and memory reuse

23 October 2026. Source/ABI review after image 32 physically completed Android
4.4.4 startup with touch. No kernel configuration or hardware changes are made
by this audit. [CPU/cache](decatf-cpu-reuse.md) and
[graphics](decatf-graphics-reuse.md) cover the other requested components.

## Provenance and comparison method

The current 4.4.147 port already descends from Decatf's
[`android-4.4-p4wifi` kernel](https://github.com/Decatf/linux/tree/bbcece6d21c83b6280061a91d27566aff1951c94).
Here **4.4 is the Linux version**, not a declaration of Android userspace
compatibility. The pinned [Oreo manifest](https://github.com/Decatf/manifest/blob/86da0eca29258e6fa7e891cb887069cb577f9bba/local_manifest.xml)
selects that kernel family alongside Android 8.1 repositories. Several projects
use the maintainer's local `file:////home/r/` remote. The public branch names
alone cannot reconstruct those former local checkouts.

Working baseline facts come from the preserved original boot image, captured
configuration and Android 4.4.4/Linux `2.6.39.4-ElementalX-Xoom-2.1+` runtime.
The source comparators are
[ElementalX `3cfbd6c3`](https://github.com/flar2/xoom-ElementalX/tree/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd)
and [Schischu `6b3d70ff`](https://github.com/Schischu/android_kernel_moto_wingray/tree/6b3d70fff905b7395fd15992c3779b27d1b6c101).
Neither has been reproduced byte-for-byte as the installed kernel; the latter
is board lineage, not the exact working Android 4.4.4 binary's proven source.

A source diff from the pinned donor to image-32 commit `fd24d166` shows the
Binder driver/UAPI, ashmem implementation/UAPI and low-memory killer unchanged.
Within the Android driver directories, the changes are the scoped legacy logger
source/header and its Kconfig/Makefile entries. Reusing these existing 4.4
implementations is preferable to porting the old 2.6 memory subsystem wholesale.

## Component classification

| Component | Classification | Evidence and decision |
|---|---|---|
| Decatf Binder driver with matching protocol/layout | **Directly reusable; already used** | Image 32 runs servicemanager/framework services and the native protocol-7 check. Keep the existing driver and select the userspace-matching ABI. |
| Decatf ashmem | **Directly reusable; already used** | Original and donor expose the same named-region/pin API on ARM32. The real native test creates, maps and checks a private 4 KiB region. Reclaim/purge concurrency remains untested. |
| Wingray legacy logger adapted to 4.4 | **Directly reusable from the current port** | Patch 0054 already reuses the original logger ABI with 4.4 API adaptations; native v1/v2 checks and real KitKat logcat work. No replacement driver is needed. |
| Decatf Oreo `liblog`/logd as a replacement for KitKat `/dev/log/*` | **Incompatible as a drop-in** | Different userspace transport. Change this only as part of a matched newer ROM. |
| Decatf low-memory killer, cgroups, shmem and VM infrastructure | **Directly reusable core; Motorola-specific policy integration** | Already present and enabled. The actual KitKat startup writes legacy adjustment values, and the donor converts them to `oom_score_adj`. Keep 4.4 APIs; tune only against measured Wingray memory pressure. |
| Literal old 2.6 VM/shrinker implementation or Samsung carveout/minfree policy | **Incompatible as a direct import** | API and memory-map differences; copy neither an old shrinker callback nor unrelated board reservations. |

“Direct” means no board-specific driver rewrite is indicated. It does not mean
every ioctl, stress case or newer Android service is validated.

## Binder: match the actual build, not the Android number alone

The [donor UAPI](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/include/uapi/linux/android/binder.h#L92)
selects 32-bit `binder_size_t`/`binder_uintptr_t` and protocol 7 when
`BINDER_IPC_32BIT` is defined; otherwise the fields are 64-bit and protocol 8.
The [kernel driver](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/android/binder.c#L74)
derives this from `CONFIG_ANDROID_BINDER_IPC_32BIT`.
The [original ElementalX header](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/drivers/staging/android/binder.h)
uses native 32-bit fields and protocol 7. The tested profile deliberately keeps
protocol 7 and only the `binder` device.

Do not infer that Oreo requires switching this port to protocol 8. Decatf's
[checked-in kernel configuration](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/configs/tegra_android_defconfig#L3297)
also enables the 32-bit Binder ABI, alongside `binder,hwbinder,vndbinder`.
AOSP 8.1's [libbinder build](https://android.googlesource.com/platform/frameworks/native/+/android-8.1.0_r1/libs/binder/Android.bp)
supports the `binder32bit` product variable; its
[ProcessState](https://android.googlesource.com/platform/frameworks/native/+/android-8.1.0_r1/libs/binder/ProcessState.cpp#375)
rejects a protocol mismatch at runtime. Thus ARM instruction width, Binder wire
format and Android release must be checked separately. The full former Decatf
userspace build has not been reproduced here.

For a future ROM, compile a probe against that ROM's exported Binder headers,
compare ioctl numbers/structure sizes to the selected kernel configuration, then
exercise actual service-manager IPC and descriptor passing. Add hwbinder and
vndbinder only in the separate ROM profile with its matching init permissions,
SELinux policy and services. Their node names alone are not an Oreo boot test.

## Ashmem, logger and memory management

The [donor ashmem UAPI](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/android/uapi/ashmem.h)
and [original UAPI](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/include/linux/ashmem.h)
retain 256-byte names, size/protection operations and two-32-bit-word pin ranges.
Use the donor's existing implementation with its current shmem/shrinker APIs.
The physical 4 KiB check is narrow evidence; it does not prove purge races or
behavior under sustained memory pressure.

The logging distinction is verified in public Android sources:

- Decatf [KitKat `logd_write.c`](https://github.com/Decatf/platform_system_core/blob/19ebdadee468bfbf28b4118aa1990e5eeb46e94a/liblog/logd_write.c)
  writes `/dev/log/*`. Its downloaded bytes match
  [AOSP Android 4.4.4_r2](https://android.googlesource.com/platform/system/core/+/android-4.4.4_r2/liblog/logd_write.c)
  exactly (SHA-256 `2b9a31a23dd61a34830db1e8be9e8ee894c04720116d57b8db404ad8da2f0a0e`).
- Decatf [Oreo `logd_writer.c`](https://github.com/Decatf/platform_system_core/blob/2bec533bff48f7a38075f7aa52d75433d9bab074/liblog/logd_writer.c)
  sends to `/dev/socket/logdw`. Its logd is a userspace service, not a substitute
  kernel ABI for the installed KitKat logging binaries.

Patch 0054 retains the KitKat logger v1/v2 records while adapting writes to
`write_iter` and current credentials/locking. Keep it in the tested KitKat
profile. A newer userspace must use its own matched logging stack; copying
Oreo `liblog` into the current ROM would leave other dependencies unresolved.

The original low-memory killer uses the older single shrink callback and
`oom_adj`; the [donor](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/staging/android/lowmemorykiller.c)
uses `count_objects`/`scan_objects` and `oom_score_adj` with legacy-value
autodetection. Image 32 records conversion of KitKat's values 0/1/2/3/9/15 to
0/58/117/176/529/1000. This validates startup integration, not OOM recovery.

The physical log reports 721,184 KiB available from a 759,804 KiB described
region, with 16 MiB CMA reserved and no highmem pages in that boot. Nominal
1 GiB capacity does not justify freeing the retained video/console reservations.
Preserve the validated ARM low-memory sizing correction, memory map and CMA
until their consumers and cache behavior are independently established.
RAM-backed data/cache also consume this budget; avoid importing p4wifi minfree,
heap, zram or carveout values without measurements.

## Separate patch/build/validation gates

| Work unit | Offline check | Device acceptance |
|---|---|---|
| A0: retain image-32 KitKat ABI control | Existing native fault tests, static ARM/non-NEON build, protocol/config/source hashes | Fresh boot-completion flags, service activity, logger/ashmem/Binder probe, touch and read-only storage |
| A1: memory-pressure diagnostics only | Bounded `/proc`/cgroup/LMK metadata; no purge-all or unbounded allocation | Observe RAM-data first boot and idle/load behavior; original userdata remains unmounted |
| A2: bounded memory/reclaim experiment | Exercise actual alloc/free/error behavior with strict RAM/time limits; separate source commit | Recovery from the bounded workload, stable UI/USB, no critical-service death or storage-policy change |
| A3: separate newer-ROM ABI profile | Pin reproducible userspace sources, Binder bitness/headers, logging/services/permissions and non-NEON dependency closure; full kernel/userspace builds | Actual service-manager IPC and framework startup on that matched userspace; restore originals after test |

No IPC or VM rewrite is needed to explain the current Welcome screen: it already
works with the reused donor core. Stabilize the observed touch startup issue and
prove a lockscreen on the RAM-data control before expanding the hardware scope.
