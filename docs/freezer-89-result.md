# Candidate89 — one hardware task-freezer test passes

28 October 2026. Exact [prepared image](freezer-89-prepared.md),
4,214,784 bytes, SHA-256
`edfe9c59d3f1852506efec5c89429b727ad0c8a03f4dfc1d86dff86b0d6f1015`.
**Task freeze/thaw passed. Device suspend, CPU sleep and physical low-power
wake were not tested; ordinary sleep remains blocked.**

## Flash and requested wait

The operator authorized boot-only flash and requested two minutes before
testing. Fastboot identified Xoom Wi-Fi and confirmed transfer/write/reboot.
Both original backup files matched their recorded SHA-256 values beforehand.
Recovery/layout were not written; no live partition readback is claimed.
More than two minutes elapsed after reboot before the baseline report was
requested. Temporary serial permission was renewed by the operator.

Candidate89 remains installed. Candidate88 and original boot/recovery
backups remain preserved; no restoration followed this test.

## Baseline and one explicit request

A nonce/hash-verified REPORT confirmed Android boot completion,
SurfaceFlinger/zygote, matching full eMMC/ten-BigPart geometry and the
preparation-block startup message. GLES identity was NVIDIA Tegra OpenGL ES2;
this was not a new graphics stress/readback test. CPCAP was IRQ-only,
polling0 and errors0.

The single FREEZERTEST returned a verified417-byte payload, SHA-256
`764359e13215e98d152dcec80c021a44e942019fdcf401f51cee1eb8c04804e4`:

```text
FREEZERTEST_BEFORE completed=0 last_result=0 device_suspend=0 cpu_sleep=0 ordinary_sleep=blocked
FREEZERTEST_WRITE_RC 0
FREEZERTEST_AFTER completed=1 last_result=0 device_suspend=0 cpu_sleep=0 ordinary_sleep=blocked
FREEZERTEST_COUNTER_ADVANCED_1
FREEZERTEST_PROCESS_RC 0
```

The fresh post-test kernel log contains:

```text
[154.147670] Freezing user space processes ... (elapsed 0.001 seconds) done.
[154.150814] Freezing remaining freezable tasks ... (elapsed 0.008 seconds) done.
[154.160775] WG_FREEZER89 tasks frozen; device/CPU suspend not entered
[154.670511] Restarting tasks ... done.
[154.671711] WG_FREEZER89 tasks thawed result=0
```

These timestamps are kernel log times, not power measurements. The test used
normal PM preparation/notifier/freezer machinery, then stopped before device
callbacks and platform sleep. No global pm_test mode or wake reference was
changed by the fixed request. The completion counter advanced once; no retry
or reset was initiated. No error rollback path was exercised on hardware.

## Post-test checks

Fresh REPORT checks passed framing, Android boot completion and storage
geometry; CPUs0–1 remained online. A PSTORE snapshot confirmed ECC16, bound
backend and unchanged memory/record sizes. It was a same-boot snapshot, not
new retention or hard-hang recovery validation. The sysfs-group warning at
0.712295 seconds was already present before the request and was not caused
by this test.

The operator then confirmed the same Welcome session/touch and power-button
backlight off/on were “all working”. The final REPORT again passed Android
and storage checks and showed CPCAP events4, errors0, polling0. No new radio
connection, battery-current, charging-control, GPU stress or system device
resume test was performed.

## Accepted scope and next stage

**One real task-freezer/thaw cycle passes on candidate89**, followed by
working Android, display/touch/power-button operation and healthy storage
checks. The test did not enter a hardware low-power state. It provides no
evidence of PMC wake routing, CPU-complex restoration, DRAM retention,
peripheral system-PM restoration or deep-sleep power savings.

Next: implement/review checked CPCAP wake arming in system device PM order,
DC/GPU restore and remaining peripheral callbacks; then a separately gated
device-PM dry run before considering a CPU-complex sleep profile. LP0/LP1,
Android automatic suspend and real low-power wake remain excluded.

Raw captures remain private in ignored artifacts: `freezer89-baseline`,
`freezer89-cycle1`, `freezer89-after-cycle1`, `freezer89-pstore-after-cycle1`,
`freezer89-after-keycheck` and `freezer89-deployment`. Saved payload lengths,
SHA-256 values and nonce-bearing wire captures were checked. Raw logs,
identifiers and ROM contents are not published.
