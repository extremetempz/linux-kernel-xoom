# Image 60: Android starts with NVIDIA EGL; visible scanout remains unvalidated

Two independently requested, integrity-verified USB reports confirm `sys.boot_completed=1`, SurfaceFlinger `GLES: NVIDIA Corporation, NVIDIA Tegra, OpenGL ES 2.0`, and NVIDIA gralloc. The user reports a blank screen. This proves framework startup with the NVIDIA implementation, not correct visible accelerated composition or a usable lockscreen.

The framebuffer bus-map correction works: the legacy controller and framebuffer probe, and the bootstrap records `display_passed`. Both reports retain matching eMMC/BigPart geometry. Raw reports remain private under `artifacts/androidgpu60-report1` and `artifacts/androidgpu60-report2`.

## Verified remaining faults

- LP8550 P3 verification rejects A1=0x60 and A2=0x9f against expected 0x67/0xbf; remaining five checked registers match. Probe returns -EINVAL. Do not bypass this guard or write replacement EEPROM values without establishing the Motorola initialization sequence.
- Legacy DC reports it cannot divide 65 MHz to the requested 66.4 MHz. The current RGB setup reparents the display clock but has its parent-rate adjustment commented out. The report does not establish the live parent clock tree.
- DC IRQ count is zero in the first report. SurfaceFlinger reports NVIDIA EGL, an acquired buffer and hardware composer enabled; these are not proof that scanout or completion interrupts work.

## Next work

Compare the original Motorola panel/backlight initialization and the hardware-tested software-display path against the legacy DC path. Determine clock parent/rate and divider semantics before adjusting them. Preserve the P3 register safety guard, fixed GPU/EMC constraints and original image backups. Investigate framebuffer presentation/completion separately after clock and backlight setup are verified. Do not import Samsung board controls.

Image SHA-256: `676e5beb7ac2cf3d6debc8507e2ff8b398f0659bccdb3aca80b837f1527c71ac`. Source correction was committed after flashing as `336f126` (kernel `3268a272`). Original restoration is pending at the time of this finding; no recovery or partition-layout writes were performed.
