# Image 92c corrected syscore hardware result

1 November 2026. The corrected `PM_SUSPEND_MEM` + `TEST_CORE` path was run on
Image 92c (`artifacts/dpm92c-ready/wingray-android44-gpu.img`). The saved
on-device status shows:

```text
SYSCTEST_BEFORE completed=0 last_result=0 selected=syscore whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked
SYSCTEST_WRITE_RC 0
SYSCTEST_AFTER completed=1 last_result=0 selected=syscore whole_tree=1 platform_entry=0 cpu_sleep=0 ordinary_sleep=blocked
SYSCTEST_COUNTER_ADVANCED_1
SYSCTEST_PROCESS_RC 0
```

This is the corrected test: `PM_SUSPEND_MEM` with `TEST_CORE`, a test-only
dummy platform `enter` callback, CPU1 offlining through the normal hotplug
path, IRQ-off, `syscore_suspend()`/`syscore_resume()`, then device/CPU resume
without calling the dummy platform enter or entering LP2.

The earlier `SYSCTEST result=0` from `PM_SUSPEND_FREEZE` is invalid as syscore
evidence because that path returns at `freeze_enter()` before syscore.

A same-boot normal report confirms the actual syscore path:

```text
PM: suspend of devices complete after 4.437 msecs
PM: late suspend of devices complete after 0.707 msecs
PM: noirq suspend of devices complete after 0.772 msecs
PM: Calling sched_clock_suspend+0x0/0x30
PM: Calling timekeeping_suspend+0x0/0x2c4
PM: Calling fw_suspend+0x0/0x18
PM: Calling tegra_timer_syscore_suspend+0x0/0x1c
PM: Calling cpu_pm_suspend+0x0/0x18
PM: Calling tegra_ictlr_suspend+0x0/0x1a0
PM: Calling tegra_ictlr_resume+0x0/0x168
PM: Calling cpu_pm_resume+0x0/0x10
PM: Calling tegra_timer_resume+0x0/0x18
PM: Calling irq_pm_syscore_resume+0x0/0x8
PM: Calling timekeeping_resume+0x0/0x48c
PM: Calling sched_clock_resume+0x0/0x50
PM: resume of devices complete after 411.925 msecs
WG_PM92_STAGE_COMPLETE selected=syscore result=0 platform_entry=0 cpu_sleep=0
```

The dummy platform enter was not invoked. CPU1 was offlined by
`disable_nonboot_cpus()` and restored during the same test.

Limits:

- The saved status and report prove the diagnostic stages, not LP2 CPU-complex
  power loss, DRAM self-refresh or physical wake.
- This does not validate LP2 CPU-complex power loss, DRAM self-refresh,
  PL310 loss, or physical wake.
- The PMC request/PMIC handshake remains unresolved.

Do not use this result alone to enable an LP2 image.
