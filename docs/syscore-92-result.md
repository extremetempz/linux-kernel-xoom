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

Limits:

- The saved status proves the diagnostic stage completed with result0; a
  normal same-boot report is still required to confirm the expected PM/LIC
  checkpoints and absence of unrelated errors.
- This does not validate LP2 CPU-complex power loss, DRAM self-refresh,
  PL310 loss, or physical wake.
- The PMC request/PMIC handshake remains unresolved.

Do not use this result alone to enable an LP2 image.
