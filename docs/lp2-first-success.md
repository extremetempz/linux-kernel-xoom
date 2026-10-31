# First genuine LP2 suspend/resume — 1 November 2026

Image 93e produced the first complete same-boot LP2 evidence:

```text
PM: suspend entry
tegradc tegradc.0: suspend
PM: suspend of devices complete
WG_LP2_SUSPEND_ENTER state=3 pm_test=0
PM: Calling tegra_timer_syscore_suspend
WG_LP2_PLATFORM_ENTER mode=LP2 online=1
WG_LP2_CPU_RESUMED
PM: Calling irq_pm_syscore_resume
PM: suspend exit
LP2TEST_RETURNED
LP2TEST_PROCESS_RC 0
```

- Boot ID `c4b01baf-b3d0-4851-be57-6e0851e8ec9d`.
- LP2 counter before `0`, after `1`.
- Physical power-button wake.
- Android, display, touch, Wi-Fi and storage usable afterward.
- The LP2 status helper was captured with SHA-256
  `5f50618a78ddea0e8187bcf1f890bb935d47c16762a9a5919c524afe66f71a61`.

## Interpretation

`WG_LP2_PLATFORM_ENTER` proves the real Tegra suspend op ran, not the Image 92
dummy. `cpu_suspend()` returned only after `tegra_sleep_cpu_finish()` entered
the Tegra 20 tear-down/WFE and the LP2 reset vector resumed the CPU. The
physical wake and unchanged boot establish the first genuine LP2
suspend/resume on this tablet.

This does not yet prove:

- production-grade resume ordering;
- measured power savings;
- correctness of every wake source.

## Remaining defects

The earlier reports showed a large CPCAP `-108` IRQ-status flood during
resume. It did not prevent this cycle, but it must be fixed before LP2 can be
called production-ready. The CPCAP IRQ handler is racing SPI/regmap resume.

Wall-clock time remains wrong (it was wrong before LP2). Do not use it as a
suspend timestamp.

No power measurement is claimed. Compare battery/current over screen-on idle,
screen-off awake, and LP2 only after the CPCAP resume race is fixed.

## Image

`artifacts/lp2e-ready/wingray-android44-gpu.img`

- 4,220,928 bytes
- SHA-256 `d40c5a4a41443a767dd4f7c7e49c43074f22bd80393ee6e5b6f4201b21571a68`

Do not flash or rerun automatically. Preserve this successful artifact and the
status JSON.
