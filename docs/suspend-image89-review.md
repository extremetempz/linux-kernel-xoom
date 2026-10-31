# Image 89 review — task freezer only, not sleep

28 October 2026. Reviewed the merged candidates 85–89 and the image-89
freezer profile. No device operation or flash was performed during this
review.

## Why there is still no sleep

Image 89 is intentionally not a sleep image. Its result records:

```text
device_suspend=0
cpu_sleep=0
ordinary_sleep=blocked
```

The code confirms the ordinary path is blocked at multiple levels:

1. `CONFIG_MOTOROLA_WINGRAY_PM_PREPARE=y` makes `pm_suspend()` return
   `-EOPNOTSUPP` before preparation, even for `freeze`/`mem`.
2. `tegra_init_suspend()` returns early for the preparation profile, so
   Tegra platform suspend ops are never registered.
3. The ECC DT still lacks the complete PMC suspend parameters; PMC mode is
   not a usable LP2/LP1/LP0 profile.
4. Candidate 81's DC resume is disabled in this profile; the combined
   IRQ/DC hard hang remains undiagnosed.
5. Only the CPCAP parent wake reference is tested while awake. No PMC wake
   route is armed for a real low-power state.
6. Device restore callbacks, CPU1/L2/timer handling, DRAM self-refresh and
   Android autosuspend are not validated.

The task-freezer test passes, including real freeze/thaw and return to the
same Android session. That is a preparation-stage success, not SoC sleep.

## Code review

The freezer test is correctly bounded:

- one-shot, root-only, exact `1` request;
- PM mutex and pm_test state checked;
- preparation/notifier/freezer run, then a 500 ms hold;
- returns before device suspend, CPU offline, platform entry or low-power
  register programming;
- success counter advances only on completion, errors preserved;
- ordinary `pm_suspend()` remains blocked;
- freeze/platform begin/end null-table handling is corrected independently.

No functional defect was found in the freezer stage.

## Verification limits

The private hardware captures for image 89 (`freezer89-baseline`,
`freezer89-cycle1`, `freezer89-after-cycle1`, etc.) are **not present in this
workspace**, so the reported task-freezer hardware pass cannot be independently
reproduced here. The project tree still has no image-89 artifact to compare
against the documented hash.

The ECC retention artifacts from candidate 84 are also still absent, so the
preceding retention gate remains documented-but-unverified in this checkout.

## Next gate

The next safe step is not a sleep attempt. It is a device-PM dry-run profile
(or equivalent staged callbacks) that:

1. keeps platform/CPU/DRAM low-power entry blocked;
2. arms and disarms the CPCAP wake path in system PM order with error checks;
3. exercises DC/GPU restore plus one peripheral at a time;
4. preserves matched ECC/pstore recovery and Test 5 rollback.

Only after those callbacks and a physical wake source are validated should a
separate LP2 profile be considered. LP1/LP0 and Android autosuspend remain
excluded. Do not write `/sys/power/state` on image 89.
