# Image 92 CPU1 hotplug hardware result

1 November 2026. One operator-controlled CPU1 offline/online test on Image 92
(`e04cb835…`) passed:

```text
CPU1TEST_ONLINE_BEFORE 0-1
CPU1TEST_CPU1_OFFLINE
CPU1TEST_ONLINE_AFTER 0-1
CPU1TEST_PASS
CPU1TEST_PROCESS_RC 0
```

Interpretation and limits:

- Both CPUs were online before the test.
- CPU1 was taken offline through the standard CPU-hotplug interface.
- CPU0 remained online and the shell helper continued.
- CPU1 returned online and both CPUs were reported online afterward.
- No automatic retry occurred and CPU0 was never offlined.
- This was not combined with device suspend, LP2 or CPU power-down.

The helper checks online state but the saved output does not yet include
per-CPU scheduling, interrupt or cache diagnostics. Android touch/Wi-Fi/BT
usability after the cycle should be confirmed by the operator before this is
used as an LP2 prerequisite.

This validates basic CPU1 offline/online only, not LP2 CPU-complex shutdown.
