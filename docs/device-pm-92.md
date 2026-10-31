# Image 92 — suspend-prerequisite diagnostics

1 November 2026. **Not flashed or hardware-tested.**

## Image

`artifacts/dpm92-review-ready/wingray-android44-gpu.img`

- Size: 4,220,928 bytes
- SHA-256: `e04cb8355989e24c94fbda3ad962c7b222aa4871d81e194ca86930bc9f9e8bc1`
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

The late/syscore sysfs attributes are fixed diagnostic triggers, not automatic
boot actions. They must not be run together with CPU1 or each other.

## Status

- CPU1 hotplug: **prepared, not hardware-validated**.
- Late/noirq PM: **source/profile prepared, not hardware-validated**.
- Syscore ordering: **source/profile prepared, not hardware-validated**.
- PMC handshake: **blocked**; see [PMC/wake review](pmc-wake-92-review.md).
- Physical LP2 wake: **not validated**.
- Image 93 LP2 candidate: **not prepared**; blockers remain.

## Rollback

Keep the original boot/recovery images and Test 5. Never flash recovery or
repartition. On a hang, power-cycle, enter fastboot, and restore the known-good
boot image. Preserve ECC/pstore first when possible.
