# Decatf CPU, cache and frequency reuse audit

Review date: 23 October 2026. This is a source comparison and implementation
plan, made after image 32 reached the Android Welcome screen and the operator
reported working touch. It changes no kernel sources, tested configurations,
device settings or images. The broader graphics and Android ABI audits are
separate documents.

## Recommendation

Reuse the Tegra20 support already present in the selected Decatf 4.4 donor.
Develop isolated PL310 and SMP profiles before attempting frequency or voltage
changes. Neither a new kernel migration nor Samsung board initialization is
needed to test those existing SoC implementations.

The frequency driver needs substantially more care: it is not a complete Xoom
DVFS implementation. Its clocks, memory-frequency requests and voltage
dependencies must be reconciled with Motorola hardware before enabling it.
Do not enable the donor's complete `tegra_android_defconfig` on Wingray.

## Provenance and limits

| Reference | Exact revision inspected | What it establishes |
| --- | --- | --- |
| Decatf `linux`, `android-4.4-p4wifi` | `bbcece6d21c83b6280061a91d27566aff1951c94` | Linux 4.4.147; the existing project's actual pinned donor. |
| Decatf `android_kernel_samsung_p4`, `aosp-mm-stable` | `6f817d40526d86d3d4edfaba29723b950cf4ed8f` | Linux 3.1.10; older vendor SMP/cpufreq behavior for comparison, not another 4.4 tree. |
| Hardware-tested image 32 | `fd24d166a00bd9860f1a287b9b974843bddcc716` plus its existing patch series | SMP, PL310 and CPU frequency scaling remain disabled in the tested touch configuration. |
| Current Wingray source during this audit | `159616f7936b918918066b416140d03008a3526d` | Adds the separately committed touch IRQ-request correction after image 32; it does not change the CPU/cache/frequency files compared here. |
| Schischu `android_kernel_moto_wingray`, `jb-mr2` | `6b3d70fff905b7395fd15992c3779b27d1b6c101` | Motorola 2.6.39.4 board lineage and BigPart reference, not proof of the exact working binary's source. |
| flar2 `xoom-ElementalX` source candidate | `3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd` | Relevant ElementalX 2.6.39.4 CPU/cache/power implementation. Its checked defconfigs are not byte-identical to the captured running config. |
| Preserved original image and working-ROM capture | `2.6.39.4-ElementalX-Xoom-2.1+`, Android 4.4.4 | Actual working baseline. Embedded/captured config enables two CPUs, PL310, CPU/core DVFS and MAX8649/CPCAP. Source-to-binary reproducibility is not established. |

The public branch API was checked during this review. Decatf also preserves
`android-4.9-p4wifi-20181026` at
`b0ea306b89a174583b1128b896e57b39d068bc4d` and several postmarketOS branches up
to `5.1-pmos`. The pinned 4.9 branch's Makefile reports **4.9.135**. Their existence does not establish that their Android graphics
ABI, Motorola board support, or all peripherals work. They are reference
material, not a reason to discard the physically tested 4.4 port.
[Public branch inventory](https://api.github.com/repos/Decatf/linux/branches?per_page=100).

Primary pinned sources:
[Decatf 4.4 Makefile](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/Makefile#L1),
[ElementalX source](https://github.com/flar2/xoom-ElementalX/tree/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd),
[Motorola lineage](https://github.com/Schischu/android_kernel_moto_wingray/tree/6b3d70fff905b7395fd15992c3779b27d1b6c101).
Public API responses and selected downloaded files are retained locally under
ignored `artifacts/decatf-cpu-audit/`; no device identifiers or raw device logs
are included in this document.

## Classification

“Directly reusable” describes source architecture compatibility, not physical
validation on this Xoom. All enabled candidates still need the gates below.

| Component | Classification | Current Wingray and original-kernel comparison | Decision |
| --- | --- | --- | --- |
| Tegra20 secondary CPU release, SCU and reset trampoline | **Directly reusable** SoC code, already present | Current `platsmp.c`, `reset.c` and `reset-handler.S` are unchanged from the pinned donor. The original uses the same Tegra CPU clock/reset/flow-controller blocks, but its old ARM SMP hooks and startup assembly differ. | Retain 4.4's implementation; test in a new SMP profile. Do not transplant 2.6 hooks or Samsung board initialization. |
| PL310 driver and Tegra20 cache DT description | **Directly reusable** SoC implementation, already present | Current inherited DT latency values encode the same tag/data latency register values as ElementalX. Current tested configuration disables the driver. | Enable alone first. Inspect controller revision, aux/prefetch state and applicable errata before claiming equivalence. |
| Tegra20 cpufreq clock-switch mechanism | **Reusable with Motorola-specific modifications** | Current donor has working-framework code for PLL-P intermediate switching and PLL-X targets; original uses legacy clock/DVFS integration. Donor also votes EMC rates and has no regulator calls. | Retain its 4.4 cpufreq API integration. Add explicit board policy, checked bus requests and failure handling; do not turn it on unchanged. |
| Voltage sequencing and rail coupling | **Reusable with Motorola-specific modifications** from Motorola, not a Samsung board table | Working source candidates use MAX8649 for CPU and CPCAP SW2/SW4 for core/AON, with rail relationships in legacy `tegra2_dvfs.c`. The tested 4.4 touch profile leaves these programmable regulators disabled. | Audit and port the Motorola rail constraints/ordering into the 4.4 regulator/clock model in separate stages. |
| Samsung memory tables, regulator bindings, board power/suspend setup | **Incompatible as a direct Wingray import** | Shared SoC does not establish the same RAM part, rail wiring, PMIC or resume controls. | No import into Wingray. Use Motorola board data and positive hardware identification. |
| Literal 2.6.39 SMP/DVFS implementation or whole old config | **Incompatible as a drop-in 4.4 implementation** | ARM machine callbacks, clock framework internals and cpufreq APIs changed. ElementalX also carries overclock/voltage extensions. | Use as a behavioral/hardware reference, not an unreviewed source replacement. |

## Tegra20 SMP and CPU bring-up

Verified source facts:

- Decatf's Tegra20 path holds the secondary CPU in reset, clears its flow halt,
  enables its clock, clears flow CSR and releases reset. The SCU preparation
  also enables coherency and standby features. The common DT machine selects
  `tegra_smp_ops`; no Samsung pinmux or PMIC call is part of this sequence.
  [Tegra20 startup](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mach-tegra/platsmp.c#L45),
  [SCU preparation](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mach-tegra/platsmp.c#L186).
- The 4.4 reset code installs an IRAM trampoline and records the physical
  `secondary_startup` address. This is already called during current early
  initialization, but a successful UP boot does not exercise CPU1 dispatch.
  [Reset handler installation](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mach-tegra/reset.c#L63).
- The inherited DT contains Cortex-A9 CPU nodes 0 and 1. The original
  2.6.39 code instead writes its startup address directly to the EVP reset
  vector using the older ARM platform callbacks.
  [Donor CPU nodes](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/boot/dts/tegra20.dtsi#L773),
  [ElementalX SMP](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/arch/arm/mach-tegra/platsmp.c#L48).
- The local early RAM tracer explicitly depends on `!SMP`. Removing that
  dependency alone would not make its shared scratch records and assembly
  assumptions safe for concurrent CPUs. SMP must initially disable that tracer
  in its separate profile and retain USB reports, or gain a separately reviewed
  per-CPU-safe tracing implementation. Preserve the working UP profile exactly.

Inference: the matching SoC implementation makes reuse a strong next candidate.
It does not prove CPU1 can currently execute, that inter-CPU interrupts work,
or that the boot firmware/cache state satisfies all 4.4 expectations.

## PL310 L2 cache

Verified source facts:

- The inherited controller is at `0x50043000`. Its DT tag latency `<4 4 2>`
  and data latency `<5 5 2>` encode `0x331` and `0x441` through 4.4's PL310
  parser, exactly matching explicit writes in ElementalX `tegra_init_cache()`.
  This is an actual register-value match, not an assumption from the chipset.
  [Donor DT](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/boot/dts/tegra20.dtsi#L161),
  [4.4 encoding](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mm/cache-l2x0.c#L1131),
  [ElementalX initialization](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/arch/arm/mach-tegra/common.c#L94).
- Other settings are not literal matches: ElementalX derives way size from the
  cache type and supplies `0x7c000001` with mask `0x8200c3fe`; the donor machine
  supplies `0x3c400001` with mask `0xc20fc3fe`. ElementalX also writes prefetch
  and dynamic clock-gating control. These are comparison inputs, not values to
  overwrite blindly in 4.4.
  [Donor machine fields](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mach-tegra/tegra.c#L161).
- 4.4 checks whether the controller is already enabled before applying parsed
  initialization settings. A DT edit therefore does not guarantee a live
  bootloader-enabled controller was reprogrammed.
  [Initialization path](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mm/cache-l2x0.c#L1700).

The original config enables Cortex-A9 errata 742230/742231/720789/743622; the
donor has its own version-dependent choices. Check the actual CPU/cache
revision and 4.4 workaround semantics before changing those options. Different
option sets alone do not diagnose a defect. L2-driver-disabled also does not
prove the hardware controller is electrically disabled after firmware handoff.

## Frequency scaling, voltage and memory coupling

Verified source facts:

- The donor's `tegra20-cpufreq.c` uses `cclk`, `pll_x`, `pll_p` and `cpu/emc`.
  Its table includes 1.2, 1.4 and 1.5 GHz while the initial policy maximum is
  1 GHz. Initial policy fields are not a hardware safety limit on the table.
  It requests several EMC rates and ignores those requests' return values;
  it does not call a voltage regulator or choose a fuse-specific voltage OPP.
  Its PLL-rate error is logged before a subsequent parent-switch call overwrites
  the return value. That path needs explicit failure/rollback review.
  [Frequency table and targets](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/cpufreq/tegra20-cpufreq.c#L30),
  [Initial policy](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/cpufreq/tegra20-cpufreq.c#L143).
- Decatf's older 3.1 driver already distinguishes upward and downward CPU
  transitions: it checks bus-scaling errors before an upward CPU change and
  lowers the bus after a downward CPU change. Reuse that ordering concept and
  review its existing failure behavior before writing another mechanism; its
  old clock/DVFS APIs and additional SoC paths are not directly compatible with
  4.4.
  [Existing vendor transition sequence](https://github.com/Decatf/android_kernel_samsung_p4/blob/6f817d40526d86d3d4edfaba29723b950cf4ed8f/arch/arm/mach-tegra/cpu-tegra.c#L481).
- Original Motorola lineage maps `vdd_cpu` to MAX8649 at DVC I2C address
  `0x60`, `vdd_core` to CPCAP SW2 and `vdd_aon` to SW4. Legacy DVFS uses
  process-specific frequency/voltage tables and relationships between these
  rails; raising CPU voltage without preserving the core/AON relationships is
  not an isolated CPU-only operation.
  [Motorola rails](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/arch/arm/mach-tegra/board-stingray-power.c#L358),
  [MAX8649](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/arch/arm/mach-tegra/board-stingray-power.c#L638),
  [Rail relationships](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/arch/arm/mach-tegra/tegra2_dvfs.c#L73).
- ElementalX extends the old tables above the stock 1 GHz range and raises
  voltage limits. Those extensions are not conservative defaults for this port.
  Source constraints are also not evidence of the tablet's instantaneous
  voltage. Keep initial work at stock-supported frequencies and existing rails.
  [ElementalX extensions](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/arch/arm/mach-tegra/tegra2_dvfs.c#L39).
- The actual Tegra20 EMC clock path calls the existing
  `arch/arm/mach-tegra/tegra2_emc.c` timing implementation through
  `drivers/clk/tegra/clk-periph.c`; it is not the unrelated later-SoC
  `clk-emc.c` path. Missing DT tables fall back to one captured boot timing.
  That fallback is not proof of safe multi-rate DRAM operation.
  [Tegra20 clock integration](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/drivers/clk/tegra/clk-periph.c#L141),
  [Fallback table](https://github.com/Decatf/linux/blob/bbcece6d21c83b6280061a91d27566aff1951c94/arch/arm/mach-tegra/tegra2_emc.c#L277).
- Motorola's EMC board source distinguishes Samsung, Elpida 40 nm and Elpida
  50 nm DRAM using manufacturer/revision/product identifiers. A Motorola table
  named Samsung describes a DRAM manufacturer; it is not permission to use
  Galaxy Tab board timings. The correct installed part must be identified.
  [Motorola RAM selection](https://github.com/flar2/xoom-ElementalX/blob/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd/arch/arm/mach-tegra/board-stingray-memory.c#L799).

Unresolved: exact running rail voltages, chip process bin, installed DRAM part,
safe thermal thresholds, and complete frequency-transition failure behavior on
4.4. None has been validated by the Android/touch milestone. Do not interpret a
successful Welcome screen as a DVFS or suspend test.

## Separate patch and validation stages

These are proposed patches, not changes merged by this audit. Keep the image-32
defconfig, DTS, image, native tools and manifest immutable as the control.
Every stage uses a new output directory, exact release identity, hash and report;
restore and fully verify original boot/recovery after the physical test.

| Stage / separate patch | Offline gate | Physical gate before advancing |
| --- | --- | --- |
| C0: bounded read-only CPU/cache/clock metadata in diagnostic report | Output bound; no arbitrary register access; exact tested-release guards; host fixtures for missing sysfs/debugfs. | Capture CPU revision, current clocks and available cache identity from supported kernel interfaces; no frequency, regulator, hotplug or suspend writes. |
| C1: new UP + PL310 profile only | Build/link; resolved `CACHE_L2X0=y`, `SMP=n`, `CPU_FREQ=n`; DT latencies above; reservations/RO storage unchanged; inspect PL310/errata symbols and image layout. Extend verifier and exact native/protocol guards for the new profile separately. | Fresh boot, cache-init logs, Android completion, USB checksummed reports, touch press/release and two-finger input, read-only storage integrity; bounded RAM checksum workload. Repeat before SMP. |
| C2: new SMP profile, fixed clocks, no idle/suspend/hotplug | Build first with `CONFIG_NR_CPUS=2`; do not silently drop the tracer via Kconfig. Explicitly disable the UP-only tracer or first implement separately reviewed SMP-safe instrumentation. Disassemble trampoline/startup, check IRAM footprint and CPU DT nodes. Retain C1 as control. | First `maxcpus=1` control, then separate two-CPU image/command-line test. Both CPUs online, per-CPU timer/IPI/IRQ progression, pinned per-core RAM work and cross-core handoff checks; retain Android/touch/USB/storage results without stalls. No online/offline cycling yet. |
| C3: Motorola regulator binding, read-only observation first | Audit existing Wingray MAX8649/CPCAP drivers and P3 constraints against original source/capture; no Samsung board data. Make dependencies explicit and fail closed for missing rails. | Prove binding and reported constraints; verify no unintended voltage transition, display/USB regression, charging-state or reboot change. Binding itself may program hardware and is a distinct test. |
| C4: board frequency policy and error handling | Remove overclock entries from the experimental Wingray policy; hard stock cap; preserve shared CPU policy; check every clock/EMC/voltage error and unwind. Unit-test ordering and failure paths using substituted providers, not reimplemented driver logic. | Do not enable automatic governors yet. Establish one supported fixed frequency with retained rails/EMC and compare stability/temperature before manual transitions. Failures must preserve the previous safe operating point. |
| C5: Motorola EMC timing selection | Match installed RAM ID to Motorola source table; compare register order/units with donor parser; range/length/timing tests and DT compile. No p4wifi timing import. | Retain fixed CPU/voltage while validating each proposed memory rate and RAM checksums; maintain display load and read-only eMMC checks. |
| C6: complete voltage/frequency sequencing | Port existing Motorola relationships into the 4.4 model; document clock/voltage/bus order, ramp delays, thermal caps, unavailable-provider handling and rollback. Test injected errors at every transition. | Low-risk stock operating points only, explicit transitions, repeated idle/load cycles with thermal and rail observations. Enable a governor only after those pass. Suspend/LP0/hotplug remain separate later patches. |

No source rewrite is proposed for the already present SoC SMP or PL310 driver.
No tested profile should be widened to collect all six user-requested components
in one hardware test. Progress is accepted by fresh observable behavior and
retained working features, not merely a successful compile.
