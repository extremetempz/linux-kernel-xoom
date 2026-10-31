# Image 92 — suspend-prerequisite diagnostics

1 November 2026. **Not flashed or hardware-tested.**

## Image

`artifacts/dpm92b-ready/wingray-android44-gpu.img`

- Size: 4,218,880 bytes
- SHA-256: `5071964ba0dbe93aca41f335526503348a2e937eea331ae1e6e19261ec6ad9fb`
- The earlier `e04cb835…` image was used for the successful CPU1 test; this
  image adds the late/syscore fixed requests and host helper while keeping the
  same CPU1/DPM kernel functionality.
- Profile: `android44-devicepm92`
- `soc_suspend_enabled=false`; platform/LP2 entry remains blocked.

## Changes

- Image 91 DPM transport now has a boot-ID request, saved `/run/dpm-test.txt`
  boot ID, and a `DPMSTATUS` fallback. `run-dpm-test.py` re-enumerates the
  USB gadget, verifies the same boot ID, retrieves the saved status, and
  validates that the DPM counter advanced exactly once. It never sends a
  second DPMTEST.
- CPU1 diagnostic: `diagnostic/cpu1-cycle.sh`, fixed `CPU1TEST` request and
  `scripts/run-cpu1-test.py`. Uses the standard CPU-hotplug sysfs interface;
  CPU0 is never offlined; no automatic retry.
- Added `/sys/power/wingray_late_test` (pm_test=platform, late/noirq) and
  `/sys/power/wingray_syscore_test` (pm_test=processors, syscore) under the
  existing DPM profile. Platform/CPU/LP entry remains blocked.
- Existing Image 91 DPM profile remains selectable.

## Commands

CPU1 test (after booting Image 92; no suspend):

```sh
python3 scripts/run-cpu1-test.py \
  --output-dir artifacts/cpu1-image92-cycle1
```

DPM regression with reconnect recovery:

```sh
python3 scripts/run-dpm-test.py \
  --output-dir artifacts/dpm92-cycle1
```

Late/noirq and syscore fixed requests:

```sh
# Trigger one stage. USB is expected to disconnect.
python3 scripts/run-stage-test.py --stage late \
  --output-dir artifacts/stage92-late-cycle1

# After USB re-enumerates, retrieve the saved result; do not trigger again.
python3 scripts/run-stage-test.py --stage late --status \
  --output-dir artifacts/stage92-late-status1

# Same for syscore:
python3 scripts/run-stage-test.py --stage syscore \
  --output-dir artifacts/stage92-syscore-cycle1
python3 scripts/run-stage-test.py --stage syscore --status \
  --output-dir artifacts/stage92-syscore-status1
```

These are fixed requests, not automatic boot actions. They must not be run
together with CPU1 or each other.

## Status

- CPU1 hotplug: **hardware-validated once** (`CPU1TEST_PASS`); see
  [cpu1-92-result.md](cpu1-92-result.md).
- Late/noirq PM: **source/profile prepared, not hardware-validated**.
- Corrected syscore ordering: **hardware status-pass on Image 92c**;
  same-boot report still required. See
  [syscore result](syscore-92-result.md).
- PMC handshake: **blocked**; see [PMC/wake review](pmc-wake-92-review.md).
- Physical LP2 wake: **not validated**.
- Image 93 LP2 candidate: **not prepared**; blockers remain.

## Rollback

Keep the original boot/recovery images and Test 5. Never flash recovery or
repartition. On a hang, power-cycle, enter fastboot, and restore the known-good
boot image. Preserve ECC/pstore first when possible.

## Correction: syscore test did not reach syscore

The first `SYSCTEST` used `PM_SUSPEND_FREEZE` with `TEST_CPUS`. In this 4.4
kernel, `suspend_enter()` returns from the `PM_SUSPEND_FREEZE` path via
`freeze_enter()` **before** `disable_nonboot_cpus()`, IRQ disabling and
`syscore_suspend()`. Therefore its `result=0` is **not syscore evidence**;
only the freezer plus late/noirq path ran. It must not be counted as a syscore
pass.

The corrected Image 92c registers a test-only dummy `suspend_ops` and runs one
`PM_SUSPEND_MEM` transaction with `TEST_CORE`. That path runs
`disable_nonboot_cpus()`, disables IRQs, executes
`syscore_suspend()`/`syscore_resume()` and stops before the dummy `.enter`
callback. Ordinary `pm_suspend()` stays blocked. This is a new, untested
diagnostic path.

Corrected image:

- `artifacts/dpm92c-ready/wingray-android44-gpu.img`
- Size 4,222,976 bytes
- SHA-256 `55f4165541fdc724b0f15e6d444a0686efc95091045cbfb6cc84720083de51b7`
