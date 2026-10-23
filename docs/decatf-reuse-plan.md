# Wingray: touch milestone and staged Decatf reuse plan

23 October 2026. Image 32 physically boots Android 4.4.4 to Welcome with real
touch response. Independent samples confirm single-contact movement/releases
and two active tracking IDs. Original boot and recovery have been restored and
fully verified. See [physical evidence and limits](trace-boot-attempt-32.md).

## Recommendation

Keep the existing Linux 4.4.147 port. It already uses Decatf's pinned
`android-4.4-p4wifi` kernel; most requested SoC/core code is present. Reuse and
enable it in separate experiments instead of replacing drivers wholesale.
First stabilize touch startup and reach the lockscreen using the existing
software-graphics/RAM-data control. A reproducible newer ROM is a later stage.

| Requested component | Classification | Decision |
|---|---|---|
| Tegra 2 SMP/CPU bring-up | **Directly reusable SoC code** | Already present unchanged. Separate two-CPU profile and tracing changes required; UP boot does not prove CPU1. |
| PL310 L2 | **Directly reusable SoC code** | Existing implementation and DT latencies match the original source's latency registers. Controller state/errata still need a separate hardware gate. |
| CPU frequency/voltage | **Reusable with Motorola-specific modifications** | Retain the 4.4 clock/cpufreq framework, integrate Motorola MAX8649/CPCAP relationships and installed-DRAM EMC data. Do not enable unchanged donor frequency tables. |
| nvhost/nvmap | **Reusable with Motorola-specific modifications** | Existing staging code is the starting point. nvmap encodings match, but original nvhost write headers are 24 bytes and donor headers 16 bytes; installed blob dialect remains unknown. |
| EGL/gralloc/HWC | **Reusable wrappers with Motorola-specific modifications; proprietary p4wifi set incompatible as a drop-in** | Diff the existing Wingray/Decatf wrappers and use a measured matching dependency set. Current DRM/GEM is incompatible with direct legacy NVIDIA userspace calls. Keep software graphics as control. |
| Android 4.4 Binder/ashmem/logger/VM | **Directly reusable core, already integrated; legacy transport requires its existing adaptation** | Binder/ashmem/LMK remain donor code. KitKat logger is already adapted in patch 0054. Oreo logging is incompatible as a direct KitKat replacement; match Binder bitness to the actual userspace build. |

These classifications describe source reuse, not completed hardware validation.
Samsung regulators, pinmux, display timing, carveouts, EMC and power controls
are **incompatible as unvalidated Wingray imports**. No such tables were merged
by this review. The actual working baseline is the preserved ElementalX binary
and runtime; its candidate source and Schischu board lineage have not been
reproduced byte-for-byte as that binary.

## Separate implementation boundaries

Each row is an independent patch or small explicitly ordered patch series.
Keep tested image 32/config/DT/source snapshot immutable, use new artifact
directories and identities, and restore/fully verify originals after each
boot-only experiment. Stop advancing when a gate fails.

| Order | Patch boundary | Build/source gate | Physical acceptance |
|---|---|---|---|
| 0 | Touch startup IRQ request, patch 0059 | **Done:** negative-control preemption test and full candidate-33 kernel build pass; unchanged tested config/DT | Pending: confirm startup RT-throttling/burst disappears while touch, USB and Android remain working. Candidate 33 was not flashed. |
| 1 | Touch calibration and RAM-only setup/lockscreen | Keep existing boot/RO/ABI guards; no fake boot-completion properties or original userdata mount | Edge alignment, two-finger release, real setup progression and actual visible lockscreen; retain logs |
| 2 | Bounded CPU/cache/graphics/memory inventory | Read-only metadata, exact identities and output limits; reproduce ARM32 ABI measurements with `scripts/audit-tegra-graphics-abi.py` | Resolve CPU/cache revision, installed RAM and missing blob protocol facts using supported observation |
| 3 | UP + PL310 profile | Separate config; preserve memory map/CMA and errata review; full ARM link/DT/image audit | Cache logs, bounded RAM checksums, Android/touch/USB/read-only storage; repeat |
| 4 | SMP profile at fixed clocks | Explicitly disable the UP-only early tracer or separately make it SMP-safe; inspect trampoline/IRAM and two-CPU DT | First `maxcpus=1`, then two CPUs; per-core/IPI progress and cross-core RAM handoff without regressions |
| 5 | Motorola regulator/EMC integration | Identify installed DRAM, validate original constraints/table encoding, failure/rollback tests; no Samsung board tables | Binding may program hardware: test separately, then fixed safe memory rates with checksums and thermal/rail observations |
| 6 | Stock DVFS policy and sequencing | Hard stock cap, checked clock/EMC/voltage errors, existing transition-order reuse and rollback tests | Fixed/manual safe transitions before governors; no suspend/hotplug combination yet |
| 7 | Separate legacy graphics resource/ABI profile | One owner for host/DC/GART, exact reservations; resolve nvhost dialect; malformed submission/lifetime/fence tests; full build | Bounded nvmap/engine checks before rendering, then Motorola scanout; retain software control |
| 8 | Matched EGL/gralloc/HWC and future ROM profile | Full ELF/non-NEON/linker/ABI closure, existing wrapper adaptation; matched Binder/logging/init policy | Actual rendered result, framework/lockscreen, repeated allocation/redraw and stable input; suspend later |

Do not combine SMP, L2, DVFS and legacy graphics in one first boot. A passing
compile or shared Tegra 2 chipset is insufficient evidence for those changes.

## Detailed source comparisons

- [CPU, PL310, voltage and EMC](decatf-cpu-reuse.md): pinned source links,
  register-value comparisons and C0–C6 gates.
- [nvhost/nvmap, EGL, gralloc and composer](decatf-graphics-reuse.md): measured
  ARM32 layouts, existing wrappers, blob dependency limits and G0–G6 gates.
- [Binder, ashmem, logging and VM](decatf-android-abi-reuse.md): original versus
  current interfaces, KitKat/Oreo transport distinction and A0–A3 gates.

The physical touch milestone is complete within its documented scope. Broad
CPU/cache/graphics implementation has not been merged by this audit. Current
source includes the separately tested-at-host-only IRQ correction; hardware
confidence still belongs to the preserved image-32 source and image hashes.
