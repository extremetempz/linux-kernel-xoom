# Suspend preparation 82 review

Reviewed the merged IRQ-only profile against the candidate 81 baseline. No
device operation or flash was performed.

## Scope verified

- **IRQ-driven CPCAP ON path:** the new profile registers the nested ON virq
  in `irqdata[2]` at domain index 23, checks LIC routing, requests the threaded
  IRQ, verifies INTM2 unmask readback, and does not schedule the old 20 ms
  polling worker.
- **No quiet fallback:** a failed IRQ registration returns an error instead of
  registering the polling path. This is the right behaviour for a wake
  prerequisite.
- **LIC routing:** only the CPCAP interrupt parent changes, from GIC to the
  existing Tegra LIC; the physical IRQ number/polarity, SPI2, CS-high,
  native32, 10 MHz limit, rails, pinmux and display code are unchanged.
- **Candidate 81 display path:** the displaydc/native-mode/all-window and
  flip-serialization code remains enabled in this profile.
- **Awake-only guard:** PM, PM_SLEEP and SUSPEND remain disabled, and the
  manifest reports `power_key_polling=false`, `hardware_wake_validated=false`,
  `soc_suspend_enabled=false`.

## Offline result

Applying patch 0152 plus the corrected 0151 to the donor builds successfully.
The actual ON handler/registration test and profile/DT/config tests pass:

```text
PASS actual ON IRQ handler/registration: domain23, LIC gate, key transitions,
     quick clicks, IO/errors, no polling/parent masking; hardware unverified
PASS compiled IRQ-only scope, same physical IRQ/polarity, unchanged
     SPI/rails/graphics/radios, missing-patch and forbidden-PM controls
```

Built image:

- `artifacts/wake82-review-ready/wingray-android44-gpu.img`
- 4,149,248 bytes
- SHA-256 `f6ab7071972890c6789aafa501653230739f6f5ae60c8e79a48fa7f8740ec3cb`
- manifest `kernel_profile=android44-wakeirq`, `cpcap_irq_only_test=true`,
  `power_key_polling=false`, `hardware_wake_validated=false`,
  `soc_suspend_enabled=false`

## Findings

The three implementation claims are substantively correct and the tests are
meaningful. Two documentation/build reproducibility points remain:

1. **The documented `wake82-final` hash `c0a7f7b6…` was not reproduced.**
   The reviewed build produces `f6ab7071…`. The difference is consistent with
   the corrected 0151 config (duplicate `CONFIG_SUSPEND` removed) and the
   merged test/runtime sources; the candidate image hash should be refreshed.
2. **Patch 0152 must be applied to the ignored donor before building.** The
   new build guard correctly fails if the symbol is missing, which is an
   improvement; the docs already say to apply the series. A clean checkout
   should use `scripts/fetch-sources.py` and `scripts/apply-kernel-patches.py`
   before the wakeirq build.

No polling fallback, PM enablement, wake arming or hardware-wake claim was
found. This is still an awake-only IRQ prerequisite; it does not enable
suspend or prove that the power key wakes from a low-power state.
