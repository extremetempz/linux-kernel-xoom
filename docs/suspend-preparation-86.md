# PM framework preparation 86 — system sleep remains blocked

28 October 2026. Based on main `c1e475f`, after candidate85's diagnostic
build. No flash, reboot, suspend, CPU-offline request or device command was
performed. The existing hardware-tested images are preserved.

## Why this is preparation rather than enabled deep sleep

Three independent source/hardware gates are still open:

1. The combined IRQ/DC failure has not been localized. Candidate85 adds a
   manually armed trace; it has not been flashed or passed its DC test.
2. CPCAP ON events and LIC routing work while awake. In
   `drivers/mfd/motorola-cpcap.c`, the IRQ-only path deliberately skips the
   old unchecked parent `enable_irq_wake()` call. No checked suspend-time
   wake arming or physical low-power wake has been validated. A working
   awake button is not proof it can wake a suspended CPU.
3. Wingray's current ECC DT has no complete Motorola PMC suspend parameters.
   `drivers/soc/tegra/pmc.c:tegra_pmc_parse_dt()` leaves the mode NONE when
   required timing properties are absent. `tegra_init_suspend()` then does
   not register platform suspend ops. Enabling CONFIG_SUSPEND alone does
   not implement the missing board handshake.

The original-board analysis remains in
[stage80](display-power-suspend-audit-80.md). LP2 is the proposed first
CPU-complex test, not proven suspend-to-RAM: DRAM stays active. LP1 adds
self-refresh/IRAM requirements. LP0 is not implemented by this donor's
platform path. No Samsung timing, voltage, regulator or wake policy is
imported here.

There is a further important distinction: legacy
`tegra_dc_suspend()/tegra_dc_resume()` are separate callbacks from the
candidate81 framebuffer blank/unblank path. The system resume callback uses
`_tegra_dc_set_default_videomode()` and `_tegra_dc_enable()`; source review
has not established equivalence to the tested all-window framebuffer
restore/flip serialization. Fixing the awake DC hang is necessary, but by
itself will not validate system PM display restoration.

## Isolated changes

Patch **0159** adds `wingray_android44_pmprep_defconfig`, based on the
candidate84 ECC/backlight-only configuration. It compiles PM, PM_SLEEP,
SUSPEND, CPU hotplug, CPU PM and PM debug support. The CPCAP IRQ-only Kconfig
restriction is relaxed only for the new blocked preparation profile; all
existing profiles retain their previous constraints.

`CONFIG_MOTOROLA_WINGRAY_PM_PREPARE` is a build-time entry block, default off.
On the Wingray compatible it:

- returns `-EOPNOTSUPP` from `pm_suspend()` before freezing tasks, running
  device callbacks or changing CPU state, including freeze and pm_test;
- rejects the exported lower-level `suspend_devices_and_enter()` path;
- prevents Tegra platform suspend-op registration before CPU teardown/IRAM
  setup. There is no runtime switch to remove the block.

The generic suspend framework may still advertise `freeze`; that is not an
available sleep mode on this preparation profile: requests are rejected.
No `mem` entry or sleep success should be inferred from configuration symbols.
The block is limited to the new configuration and Wingray DT match.

Autosleep, PM_WAKELOCKS, boot-time suspend tests, hibernation, cpuidle, DVFS
and the panic-on-DPM-timeout watchdog remain off. The old WAKELOCK symbol is
not evidence of a functioning Android autosuspend backend. Android automatic
sleep/backend selection remains a later integration task. PM does compile
additional driver/runtime-PM code: boot behaviour itself remains untested.
DC resume experimentation remains off, as do new regulator/charging controls.
The exact candidate84 ECC DT and reserved-memory layout are reused.

## Reproducible offline compilation

Apply exported patches through 0159 to the donor first. Then:

```sh
XOOM_BUILD_ROOT=/tmp/xoom-pm86-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/pm86-new" \
bash scripts/build-pm-framework.sh
```

Both output directories must be new. This standalone builder deliberately
bypasses none of the existing Android image safety validators: it does not
call the Android packer at all. It produces kernel/modules/DT/config and a
manifest, **no Android boot image**. Its built-in RAM filesystem is empty;
these artifacts must not be substituted for a working Android image.

`tests/test-pm-preparation.py` compiles the actual `pm_suspend()` and gate
helper with controlled stubs. It verifies every valid state is rejected
without entry/marker/statistic side effects, invalid-state handling, and
unchanged non-Wingray/option-off behaviour. It checks the lower-level and
platform gates precede device/CPU transitions, validates resolved Kconfig,
and rejects a missing gate. These are software checks, not physical wake or
suspend validation.

Offline result: full ARM zImage/appended-DT and module build passed, including
bcmdhd and the newly compiled PM paths. Source head
`344ec9af6360071ccdbaaddf0044c7859923b812`. Kernel+DT SHA-256:
`024c00833563d5286a0f1ae6bd5e6d329d7928ff39cca489c944ce720245c089`.
Local outputs are in `artifacts/pm86-framework`; its manifest explicitly says
`boot_image_created=false`, `sleep_entry_blocked=true` and
`soc_suspend_enabled=false`. The ECC DT compares byte-for-byte with candidate85
(which preserves candidate84's DT). Exported patch0159 was applied to its exact
parent in a fresh temporary tree and all six result files matched the donor.
The resolved config checks, compiled entry controls and shell syntax pass.

`diagnostic/pm-snapshot.sh` is an optional standalone read-only collector for
later controlled hardware work. It records boot identity, states, PM test
level, wake counters/blockers, available wakeup-source/suspend statistics,
interrupt counts, CPU masks, framebuffer/backlight state, battery/charger
readings and relevant kernel logs. Missing interfaces are marked unavailable.
It does not mount debugfs, read PMC through /dev/mem, change GPIOs, arm wake
IRQs, write sleep state or invoke tests. It is not automatically installed or
executed by this build; take private snapshots from an appropriate runtime.

## Gates before an entry-enabled profile

1. Run candidate85's one-cycle DC experiment and matched ECC recovery;
   locate/fix any stop and establish repeated display restoration.
2. Add checked CPCAP parent/LIC wake arming with precise unwind; validate
   source polarity, deassertion and pending-event races. Do not use polling
   or USB as the only wake path. Actual wake requires a later controlled
   low-power test and physical recovery operator.
3. Audit each compiled system PM callback and fix Motorola ownership/order:
   DC/windows/host/GPU, SDIO/Wi-Fi, BT UART/shared rails, touch, OWR/battery,
   charger sampling, eMMC, USB, CPU1, PL310 and timers. Compilation proves
   neither callback registration correctness nor hardware restoration.
4. Decode original Motorola PMC parameters, prove the current clock/request
   handshake and choose the first supported mode. Keep LP1/LP0 excluded.
5. In a separate explicitly entry-enabled profile, use staged PM tests and
   then a single manual low-power attempt with retained checkpoints and
   operator recovery. Only after reliable restoration, integrate one Android
   wakelock/autosuspend backend and measure real battery-current savings.

The preparation block must not be removed as a shortcut around these gates.
No power-consumption improvement or working suspend is claimed.
