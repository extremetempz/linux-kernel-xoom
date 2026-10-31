# Image 93 — first genuine LP2 candidate

1 November 2026. Built from the hardware-validated Image 92c software pipeline.
**Not flashed and no LP2 attempt has been made.**

## Image

`artifacts/lp2-final-ready/wingray-android44-gpu.img`

- Size: 4,216,832 bytes
- SHA-256: `afa116a83157c879c6bd0f3a4cb503a4aaf46804fd6a7c361e35bde84ee09542`
- Profile: `android44-lp2test`
- DT: `tegra20-motorola-wingray-android44-lp2`
- `soc_suspend_enabled=true`, `lp2_candidate=true`, `hardware_tested=false`

## Source changes

### Console retention

`console_suspend_enabled` is forced off for this profile so the pstore console
does not stop at `PM: suspend entry`. Without it, the LP2 entry and teardown
markers are not retained even when the suspend succeeds. The kernel logs:

```text
Wingray LP2: console suspend disabled for evidence
```

### Manual-only LP2 gate

- `MOTOROLA_WINGRAY_LP2_TEST` replaces the preparation-only entry block with
  the real Tegra suspend ops.
- `wingray_pm_prepare_only()` is false for this profile, while ordinary
  `pm_suspend()` remains `-EOPNOTSUPP` unless the root-only
  `/sys/power/wingray_lp2_test` gate is armed.
- The gate accepts only `1`, requires a Wingray board, LP2 PMC mode, clean
  `pm_test_level`, and calls `pm_suspend(PM_SUSPEND_MEM)` exactly once.
- No automatic Android suspend, no state-store path, no retry.

### Motorola PMC sequencing

The original Motorola board source and PM implementation were used as the
reference:

- [board-stingray.c](https://raw.githubusercontent.com/cj64/xoom-wingray-jb-kernel/master/arch/arm/mach-tegra/board-stingray.c)
- [pm.c](https://raw.githubusercontent.com/cj64/xoom-wingray-jb-kernel/master/arch/arm/mach-tegra/pm.c)

Implemented:

- Core request output enable (`PMC_CNTRL` bit 9) with active-high polarity
  from `nvidia,core-power-req-active-high`.
- CPU power request output enable and normal polarity.
- Core good/off timer registers (`PMC_COREPWRGOOD_TIMER=0x3c`,
  `PMC_COREPWROFF_TIMER=PMC_WAKE_DELAY`) from `core-pwr-good-time` /
  `core-pwr-off-time`.
- Existing CPU good/off timers (1500 us / 1 us) converted from the actual PMC
  pclk; no fixed 100 MHz assumption.
- LP2 entry reasserts CPU and core request outputs and clears the LP0 side
  effect.
- LP2 DT sets mode 2, CPU 1500/1 us, core 0x7e7e/0x0f, active-high
  COREREQ/SYSCLKREQ.

**Uncertainty:** the original board source selects LP0, not LP2. The core
request/timer programming is copied from the original initialization sequence;
its necessity for LP2 is inferred, not hardware-proven.

### CPU/cache/resume path

- `tegra_suspend_enter()` rejects non-LP1/LP2 modes, propagates
  `cpu_suspend()` errors, validates one online CPU, and restores FIQ/flow/
  clock/mask state.
- LP2 calls `cpu_pm_enter()`, `cpu_cluster_pm_enter()`, the flow-controller
  sequence, `tegra_set_cpu_in_lp2()`, `cpu_suspend()`, then the reverse.
- Cache order: `flush_cache_all(); outer_flush_all(); outer_disable();`
  before MMU-off. This matches the original Motorola sequence. Existing
  assembly still writes PL310 control zero during MMU shutdown; that redundancy
  is retained and has not been hardware-tested.
- `tegra_sleep_cpu_finish()` clears L1 and enters the Tegra 20 tear-down/WFE.
- LP2 reset data already points at physical `tegra_resume`; the reset handler
  recognizes `MASK_LP2` and restores L2/MMU/CPU context.
- Timer USEC_CFG uses syscore suspend/resume (hardware-tested only without
  CPU power loss).

### CPCAP wake

- The LP2 profile keeps the real CPCAP `.suspend/.resume` callbacks.
- Wake arming is allowed only for the manual LP2 transaction; CDC/selected
  test owners are not released.
- CPCAP parent remains through LIC; LIC syscore suspend/resume passed in
  Image 92c.
- Physical power-button wake from actual LP2 is **not yet proven**.

## Source-verifiable gaps that remain

1. The original Motorola evidence is for LP0; no original LP2 register trace
   exists. Core-request behavior for LP2 is inferred.
2. Actual PMC-to-CPCAP PMIC handshake timing/polarity has not been observed.
3. Physical wake through LIC/PMC from LP2 has not been observed.
4. PL310 shutdown versus the assembly's second control write has not been
   tested under actual CPU power loss.
5. TIMERUS state after actual LP2 is unproven.
6. DRAM retention and reset-vector execution after actual LP2 are unproven.

These are hardware-test requirements, not reasons to add invented values.

## First hardware test

Only after explicit operator authorization:

```sh
fastboot flash boot \
  /home/justin/linux-kernel-xoom/artifacts/lp2-final-ready/wingray-android44-gpu.img
fastboot reboot
```

After Android settles and the baseline REPORT/PSTORE are saved:

```sh
python3 scripts/run-stage-test.py --stage lp2 \
  --output-dir artifacts/lp2-cycle1
```

The USB gadget will disconnect. Press the physical power button to wake.
After re-enumeration:

```sh
sudo setfacl -m u:justin:rw /dev/ttyACM0
python3 scripts/run-stage-test.py --stage lp2 --status \
  --output-dir artifacts/lp2-status1
```

Success evidence must include:

```text
WG_LP2_PLATFORM_ENTER mode=LP2 online=1
WG_LP2_CPU_RESUMED
LP2TEST_RETURNED
LP2TEST_PROCESS_RC 0
```

and a same-boot Android session with display/touch/storage/Wi-Fi intact. A dark
screen alone is not evidence. If it hangs, power-cycle, preserve pstore where
possible, and restore Image 92c or Test 5. Do not retry.

## Rollback

- Image 92c: `55f4165541fdc724b0f15e6d444a0686efc95091045cbfb6cc84720083de51b7`
- Test 5: `02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`
- Original boot/recovery backups verified before tests.

Never repartition or flash recovery. No automatic flash/reboot.

## Power

No power measurement is claimed. After one successful cycle, compare DS2781
gauge/current over meaningful intervals for screen-on idle, screen-off awake,
and true LP2. A gauge may not be readable during suspend.
