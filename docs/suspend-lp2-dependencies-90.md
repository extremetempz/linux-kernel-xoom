# Wingray LP2 dependency review — 1 November 2026

Review base: latest main `ee3a645` (PR27). Original Motorola jb-mr2 source
`6b3d70fff905b7395fd15992c3779b27d1b6c101`; current donor derives from
Decatf android-4.4-p4wifi `bbcece6d21c83b6280061a91d27566aff1951c94` plus
the exported patch series. This continues images80–89. No device commands,
flash, reboot, CPU offlining or sleep request were made.

## Established baseline and limits

Read the requested stage80–89 audit/result/review documents and inspected
actual source, configs, helpers and tests. Image89 froze and thawed tasks;
it did not suspend devices or CPUs. The awake CPCAP parent wake reference
passed on88. Instrumented framebuffer DC cycles passed on85, but the earlier
IRQ/DC hang has no established cause. These are separate milestones.

Unlike the other checkout used for `suspend-image89-review.md`, this active
workspace contains the private89 files. The preserved4,214,784-byte image
hash matches `edfe9c59d3f1852506efec5c89429b727ad0c8a03f4dfc1d86dff86b0d6f1015`;
the417-byte saved test payload matches
`764359e13215e98d152dcec80c021a44e942019fdcf401f51cee1eb8c04804e4`.
This recheck corroborates saved artifacts, not a new hardware test. Historical
STATUS entries describe earlier states; the latest dated result takes precedence.

## Dependency map

| Requirement | Classification | Evidence / next gate |
|---|---|---|
| Android/task freeze/thaw | Implemented and hardware-tested |89 one real bounded cycle; keep its independent FREEZERTEST. PM notifiers also run: it is not literally free of every device side effect. |
| LP8550 off/on; CPCAP ON IRQ/LIC | Implemented and hardware-tested while awake | No polling; physical parent source86, nested ON index23. Linux IRQ numbers dynamic. |
| Checked parent wake registration | Implemented and hardware-tested while awake |88 arm/readback/disarm. LIC wake mask is software state until syscore suspend. Not physical wake. |
| CPCAP normal driver PM callbacks | Newly implemented, not hardware-tested |90 only; same checked helper, generic PM dispatch, owned-reference unwind. SPI parent stays active. Not full system PM ordering. |
| Framebuffer DC blank/restore | Implemented and hardware-tested, limited |81/85 native href11/vref1 and all windows; old combined hang unresolved. |
| System DC/GPU PM restoration | Blocked by callback differences | Legacy bus callbacks use a separate DC path; all-window/front-buffer ownership is not established there. |
| Platform LP2 code | Implemented but not hardware-tested; source gaps | Existing Tegra20 CPU/flow-controller assembly and reset dispatch, but no complete Wingray readiness proof. See below. |
| CPU1 offline/restart | Implemented but not hardware-tested | hotplug.c -> tegra20_hotplug_shutdown; tegra20_boot_secondary restart. Initial two-core Android boot does not test hotplug. |
| PL310 resume | Implemented but not hardware-tested; cache-clean gap needs resolution | tegra_resume -> l2c310_early_resume; pre-entry dirty-cache handling differs from original. |
| LIC/GIC | Implemented but not hardware-tested across sleep | LIC syscore saves IRQ state and installs wake mask; GIC has its own CPU/cluster context paths. Must test ordering with CPU1 and restore. |
| Clock/flow-controller context | Implemented but not hardware-tested | clk-tegra20.c saves CSITE/PLLX/burst/divider; pm.c flow entry/exit. No DVFS needed or enabled. |
| Timers | Partially implemented, integration missing/unproven | tegra_timer_suspend/resume exist but whole-source search finds definitions only; timer shutdown/tick_resume does not establish TIMERUS restoration. |
| Motorola PMC handshake | Blocked by missing board configuration and audit gaps | Original polarity/CPU units established below; active clock/request/rail retention still unverified. |
| Resume-vector/IRAM ownership | Implemented, LP2 route not hardware-tested | Reset handler at0x40000000 first1KiB; LP2 data points to virt_to_phys(tegra_resume). Need actual symbol/range and warm reset checks. |
| Storage/USB/radios/touch/monitor restoration | Partly implemented or missing | Device table below; do not promote whole-tree DPM or CPU sleep yet. |
| Android automatic suspend/blockers | Missing runtime backend validation | Keep autosleep/wakelock entry disabled until manual hardware cycles pass. |
| LP1 / LP0 | Blocked | LP1 self-refresh/IRAM/pads unverified; donor platform does not implement LP0 equivalently. |

## Original Motorola PMC configuration: values and units

Verified `arch/arm/mach-tegra/board-stingray.c:stingray_suspend`:
CPU good1500, CPU off1, core good0x7e7e, core off0xf, COREREQ/SYSCLKREQ
active-high, requested modeLP0. `pm.h` labels CPU timers microseconds for
LP2/LP1 and core timers ticks forLP0. `pm.c:set_power_timers()` computes
`ceil(us * selected_clock_Hz / 1,000,000)` for both CPU timers. LP2 uses
pclk; LP1/LP0 use32768Hz. The original's fallback100MHz is a fallback,
not a measured clock and not a value to install as a board constant.

`pm.c:tegra_init_suspend()` writes the two core fields directly to
PMC_COREPWRGOOD_TIMER/COREPWROFF_TIMER. It does not convert them from
microseconds. The packed0x7e7e value must not be copied as a scalar DT time.
A field-level TRM/clock interpretation remains necessary for LP1/LP0 work;
no conversion is claimed here.

Original initialization checks normal CPU_PWRREQ polarity with BUG_ON,
sets CPU_PWRREQ_OE, programs COREREQ/SYSCLKREQ polarity before enabling
outputs and uses `pmc_32kwritel()` with a130us settling delay. LP2 sets the
normal CPU reset vector to physical `tegra_resume`, enables CPU/core request
outputs and clears the LP0 side-effect bit. This is source intent for the
original PMIC/clock arrangement, not proof the current arrangement is equivalent.
The original board also has a `max8649` vdd_cpu consumer; CPCAP ON wake does
not by itself validate the CPU supply/retention handshake.

Current `drivers/soc/tegra/pmc.c` accepts DT mode2 asLP2 and converts CPU
microseconds using pclk in the same ceiling form. But:

- DT parsing requires core-good/off values even forLP2. Adding only the CPU
  properties cannot register a working platform mode with this parser.
- `core_osc_time`, `core_pmu_time`, `core_off_time` and `corereq_high` are
  parsed but do not implement the original core-request programming here.
- `tegra_pmc_init()` programs SYSCLKREQ and CPU request output; it does not
  establish equivalence to the original COREREQ/CPU polarity sequence.
- Missing DT reads leave local `value`/`values` stale or uninitialized before
  assignment (including lp0-vec). ModeNONE currently prevents platform entry,
  but a future parser correction must initialize each optional field and
  validate only the selected mode's required fields. Do not remove validation
  by supplying invented core times.
- Early PMC interrupt inversion is a separate property from the CPCAP LIC
  level-high IRQ. Do not copy an inversion setting from Samsung.

**No PMC property, polarity, request output, voltage or charging change is
included in90.** Future LP2 properties can use verified CPU times1500us/1us,
but only after the parser and actual request/clock/PMIC handshake are reviewed.
No entry-capable DT/profile is created before the preceding hardware gates.

## LP2 assembly, cache, vector and timer review

`tegra_suspend_enter()` saves CPU clock/flow state, sets the LP2 CPU mask,
then calls `cpu_suspend(PHYS_OFFSET - PAGE_OFFSET, tegra_sleep_func)`.
The LP2 finish path disables/cleans L1 and coherency, disables MMU and PL310,
switches CPU clock to PLLP, arms the flow controller and executes WFE.
`reset-handler.S:tegra_resume` restores SCU/PL310 through
`l2c310_early_resume`, then branches to ARM `cpu_resume`.
This is relevant existing code to reuse, not proof that every required
Wingray step is complete.

Two concrete code concerns must be resolved before enabling that path:

1. `tegra_suspend_enter()` discards the `cpu_suspend()` return and always
   returns0. It also permits modeNONE in its range check. Correct mode/finish
   validation and error propagation, retaining clock/mask/FIQ unwind, need a
   separate patch/test before a platform entry image.90 cannot reach it.
2. Original Motorola LP2 explicitly calls `flush_cache_all(); outer_disable()`
   before power loss. Current assembly writes PL310 control0 after cleaning
   L1. ARM `__cpu_suspend_save()` outer-cleans context ranges, not all dirty
   outer-cache data. No equivalent full outer-cache flush was found on this
   system suspend path. This is a source-level gap to resolve with correct
   last-CPU/cache-off ordering; do not insert a flush casually while another
   CPU or DMA owner remains active. It is not a diagnosed hardware failure.

`tegra_timer_suspend/resume()` save/restore TIMERUS_USEC_CFG but have no
callers in this tree. Determine which clocks surviveLP2 and wire any required
restore through the proper PM/syscore owner before claiming timers work.

IRAM is0x40000000..0x4003ffff. The first1KiB reset handler is installed and
its LP2 dispatch target is derived from the linked kernel, not historical
bootloader data. LP1 uses0x40001000 and explicitly saves/overwrites/restores
its payload area; AVP may otherwise use this space. LP2 does not copy the LP1
self-refresh blob, but still depends on reset-handler/data ownership.
The ECC DRAM region0x1ff00000..0x1fffffff and old console0x1fe00000 do not
numerically overlap IRAM. That address comparison does not prove AVP/GPU
ownership or cache-correct physical resume.90 keeps DT bytes identical to89.

## Actual device callback audit and required order

| Device / source | Observed implementation | Required later validation/correction |
|---|---|---|
| CPCAP motorola-cpcap.c | IRQ-only ON; existing checked parent helper.90 adds normal suspend/resume dispatch of one wake vote. | Before SPI parent sleeps, arm a released/unpending key; restore SPI before resume checks. Keep regmap-irq sole mask/ACK owner.90 tests neither SPI-parent sleep nor pending-entry atomicity. |
| Display host/bus.c, dc/dc.c, fb.c | nvhost bus dispatches legacy driver callbacks. System DC resume calls default-mode/enable, not tested framebuffer legacy-lock/all-window/first-frame path; returns0 regardless of frame readiness. | Unify ownership/serialization/restoration deliberately, preserve native timing/front buffers, backlight last, propagate errors. Do not call FB blank under dc->lock: helpers acquire it and can invert locks. Then separate real callback hardware test. |
| GPU host/nvhost_acm.c | Module suspend waits for refcount idle with timeout, enters powergated state. | Frozen service tasks may own channels; drain submissions/fences, verify no work needed from frozen tasks, resume host before engines/DC. Preserve Motorola clock/reset/EMC adapters. |
| eMMC sdhci-tegra.c / sdhci-pltfm.c | SDHCI_PLTFM_PMOPS delegates host suspend/resume; MMC PM notifiers already run in89. | DMA/clock/reset/card state and error unwind still need device-PM test. System ro,noload; /data/cache remain RAM-backed in this profile. No persistent-data durability claim. |
| BCM4329 mmc/core/sdio.c + bcmdhd | Function PM validation, keep-power/SDIO suspend mechanisms exist. | Verify actual resolved bcmdhd callbacks/flags, firmware/WOW/OOB ownership and reconnection with UART radio active; no Samsung GPIO import. |
| Bluetooth net/rfkill/rfkill-wingray-bt.c | Explicitly awake-only; device-wake asserted, host-wake input has no validated IRQ/LPM; no system PM callbacks. | UART drain/LPM and hardware host-wake needed; never cut shared combo rail behind Wi-Fi. |
| maXTouch atmel_mxt_ts.c | PM callbacks call stop/start for input users; errors from void helpers not propagated. Manual suspended flag bypasses system work. | Slot release, worker synchronization, I2C parent order, restored scanning and error reporting. |
| Battery wingray_battery_monitor.c |2s delayed work on ordinary workqueue; no system PM callbacks. | Explicit stop/cancel/resume refresh needed. Task freezer alone does not guarantee this work stops. |
| OWR tegra_w1.c | No system PM ops. | Synchronize gauge/W1 traffic and restore clock/timing before gauge refresh. |
| Charger monitor | Same monitoring driver, passive STAT/DETECT reads. | Preserve autonomous charger hardware; resume resample. Charger GPIO wake14 is unvalidated. No current/voltage control writes. |
| USB chipidea/core.c + phy-tegra-usb.c | Real ci_suspend/resume and PHY power-off/on methods exist. | Verify Wingray switch/PHY ordering and re-enumeration.90 deliberately leaves this live for reports. |
| LIC/GIC/timers | Syscore/CPU context paths exist; timer gap above. | Must follow device noirq and CPU1 shutdown, and restore before normal IRQ/device service. Not invoked by90. |

## Wake route and LP2 versus PMC pad wake

Original `board-stingray-power.c` assigns CPCAP to INT_EXTERNAL_PMU;
`wakeups-t2.c` maps that source to wake18. Current Wingray DT assigns
GIC_SPI86, level-high and routes the same physical source through LIC.
The actual Linux parent/ON IRQ numbers are dynamic.

ForLP2 the relevant donor path is LIC `tegra_set_wake()` storing a mask,
then `tegra_ictlr_suspend()` installing wake IRQs while saving normal state.
It intentionally does not propagate wake to GIC (which has no wake facility).
Resume restores the saved masks/classes. The original wake18 pad mapping is
historical evidence relevant to deeper PMC wake paths, not an extra register
write required simply because88 armed LIC. Physical assertion through LP2
and pending-event handling are still untested.

90 reads ON mask/sense/latch before and after arming, refuses a held/pending
key or foreign wake owner, and leaves ACK to regmap-irq. It does not claim
these samples close an interrupt arrival race before CPU sleep. A real
platform transition needs proper wakeup_count/source accounting and the
normal IRQ suspend/syscore ordering, plus a physical power-key wake test.

## Ordered follow-up

1. Review/build90; later authorize one selected-CPCAP callback test. Preserve
   matching ECC recovery. If it fails, stop; do not proceed toLP2.
2. Correct and test display/GPU **system** callback ownership separately,
   then add touch, monitor/OWR, storage, radios and USB one group at a time.
   A full-tree devices-only DPM test comes after these group reviews, still
   before CPU hotplug/syscore/platform entry.
3. Review/patch LP2 cache cleaning, cpu_suspend errors, timer wiring, PMC
   mode-specific parsing/request handshake; validate CPU1 offline/restart
   separately. No DVFS or regulator-policy import.
4. Only then create the opt-inLP2 profile and single manual test. Preserve
   hardware sleep block on all known-good profiles. Verify backups, power,
   operator access, real wake route and matching retained-console reader;
   no automatic retries. Capture stage checkpoints only where execution
   actually reaches them. Measure three battery-current conditions with
   actual gauge/time observations; no measurements are invented here.
5. After one physical cycle and peripheral recovery, progress3/10/20 cycles,
   stop on any failure, then extend duration and evaluate Android's actual
   libsuspend/wakelock backend. No competing autosuspend mechanisms.
6. LP1 remains a later separate profile: verify actual DRAM topology/pads,
   MC stall/self-refresh, clocks and IRAM/AVP ownership first. Assembly's
   hardcoded safe-pad values are not validated just by sharing Tegra20.
7. LP0 remains optional/unimplemented: original warmboot/vector/scratch/BootROM
   ABI and ownership need reconstruction. Historical8192bytes at0x1e7f1020
   is not an allocation or permission to write/import it. Do not enable it.

The conditional LP2/LP1 profiles are deliberately **not delivered as runnable
sleep images yet**: device-PM and true wake prerequisites have not passed.
