# Checked CPCAP parent wake arming — review build87

28 October 2026. Based on main154b97d and patch0159. This is an offline
code/build deliverable. Candidate85 remains on the tablet. No new image was
flashed, no live wake reference was changed and no system sleep was attempted.
The ten live DC cycles are recorded separately in
[the candidate85 result](dc-hang-85-result.md).

## Why use a direct checked parent reference?

The existing IRQ-only CPCAP path deliberately skips its old unchecked
parent wake enable. In this donor `regmap_irq_set_wake()` accumulates a
wake count; `regmap_irq_sync_unlock()` calls `irq_set_irq_wake()` on its
parent but discards the return values. Consequently enabling the nested ON
virq alone cannot give this diagnostic a checked parent-arm result.

Patch **0160** adds a separate default-off
`CONFIG_MFD_CPCAP_WINGRAY_WAKE_ARM_TEST`, dependent on IRQ-only CPCAP and
`MOTOROLA_WINGRAY_PM_PREPARE`. It owns exactly one reference on the verified
LIC parent through the standard `enable_irq_wake()/disable_irq_wake()` API.
It does not also arm the nested virq. The standard IRQ core owns wake depth;
no direct LIC/PMC register write or wake-mask replacement is introduced.

The root-only (0600) CPCAP attribute `wingray_wake_arm` starts unowned. Nothing
arms at boot, during ordinary reports or through normal power-button input.
It is not present on the running candidate85 or any existing configuration.
Only the new isolated `wingray_android44_wakearm_defconfig` selects it.

## Checks and rollback

Arming requires the validated IRQ-only path and a wake-capable device, a LIC
parent with hardware IRQ86, and the actual dynamically allocated ON virq at
normal-domain index23. The Linux IRQ numbers are never hardcoded. A parent
already marked for wake is refused rather than taking ownership of someone
else's reference.

Read-only CPCAP samples check ON is unmasked, the key is released and its
ON latch is not pending. Regmap-irq continues to own masks and write-one-to-
clear acknowledgement. The same idle checks run after successful parent
arming, and the parent IRQ core wake flag is checked. Any error is returned.
These samples can race input; they are diagnostic checks, not proof of an
atomic suspend-entry/pending-event protocol.

If the post-arm check fails, the acquired reference is released. If release
fails, `owned=1` is retained, the original and cleanup errors are exposed,
and a later explicit disarm can retry. Repeated arm/disarm requests do not
add/drop extra references. Releasing our reference never forcibly clears
another owner's reference; `parent_wake` may remain set if one appears.

The per-device mutex serializes sysfs operations. Driver teardown first
removes the attribute, then attempts to release only its owned reference.
A backend cleanup failure is logged; teardown cannot guarantee recovery from
a failing IRQ backend. No interrupt is disabled to conceal a storm.

Readback reports:

```text
owned=0 parent_wake=0 last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked
```

On Tegra20 this exercises registration in LIC's software wake mask.
**It does not prove PMC electrical wake routing, CPU-complex wake, physical
power-button wake from sleep, or restored SPI/display/radios after resume.**
The parent is shared among CPCAP interrupt domains: setting it wake-capable
does not establish ON as the only possible source. No automatic suspend/
resume callback, CPU power mode, regulator, voltage, SPI transport, DT or
charging change is added.

## Build and offline validation

Apply patches through0160, then use new output directories:

```sh
XOOM_PM_PROFILE=wakearm \
XOOM_BUILD_ROOT=/tmp/xoom-wakearm87-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/wakearm87-new" \
bash scripts/build-pm-framework.sh
```

Default `XOOM_PM_PROFILE=prepare` still builds the unchanged preparation86
profile. The wakearm selection checks its resolved mandatory option before
building. The shared builder produces **kernel/modules/DT only, no Android
boot image**, with an empty RAM filesystem. Do not flash these compilation
artifacts in place of a working Android image.

Full ARM zImage/appended-DT and module build passed, including bcmdhd.
Source head `a08793ce2140c15b26959b7efbfe1eb0abb230b2`.
Kernel+DT SHA-256:
`08d0ce1e993190d3d3f7f1f66862fc83e7e839ef3eae0d89dd269f74b1b48bd3`.
Local outputs: `artifacts/wakearm87-framework`. The manifest records
`wake_arm_test=true`, `sleep_entry_blocked=true`, `soc_suspend_enabled=false`,
`boot_image_created=false`, and hardware untested. All output hashes were
rechecked. ECC DT is byte-identical to preparation86/candidate85.

The actual source helper, read-only idle checks, sysfs setter and teardown
were compiled and executed with controlled fault stubs/undefined-behaviour
checks. Cases cover valid arm/disarm, idempotence, invalid input, wrong
parent/chip/domain, disabled wake permission, pre-existing wake owner,
masked/pressed/pending ON, all six pre/post SPI read errors, parent-arm
failure, missing wake flag, failed rollback with retained ownership/retry,
failed disarm, foreign remaining reference and teardown failure reporting.
The existing actual ON handler/registration and PM entry-block tests pass.
Kconfig's negative control drops the wakearm option when the preparation
block is removed. Exported patch0160 applied cleanly to its exact parent,
and all resulting files matched the donor. Shell syntax/diff checks pass.

## Next hardware gate, after review

A separate combined Android test image still needs runtime/image integration
and safety validation. No flashable Android image is supplied by this step.
After that image is reviewed and explicitly flashed, first verify normal
Android/USB/backlight/IRQ operation and the initial unowned readback. Through
an appropriate root diagnostic interface, perform one explicit arm, capture
its readback, then disarm and verify `owned=0` and expected parent state.
Do not write `/sys/power/state`. Save failures and stop; never replace a
failed check with an unconditional IRQ enable/disable or register poke.

`diagnostic/pm-snapshot.sh` now also reads the IRQ and wake-arm status files,
when available. It does not arm them. Power-button input and wake-flag
registration can then be tested while the SoC remains awake. Actual physical
wake requires a later, separately reviewed low-power attempt with the
Motorola PMC/CPU/cache/device resume prerequisites and manual recovery.
LP1/LP0 and Android autosuspend remain excluded.
