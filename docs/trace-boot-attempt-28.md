# Image 28 result: display probe blockers captured

22 October 2026. Linux 4.4 reached fresh diagnostic userspace and USB; no framebuffer was registered, so the color-bar program did not run. Android under Linux 4.4 was not attempted.

Two fresh nonce/length/SHA-256 verified USB reports retain full 62,521,344-sector capacity and all ten live BigPart extents. No Android block mounts or reserved-RAM reads.

| Capture | Bytes | SHA-256 |
| --- | ---: | --- |
| 1 | 49834 | `76a28f9e1e29a5a93a8c491c16c56d5573451210abf85c22a5a92daeeb581e9e` |
| 2 | 49834 | `8575c33b621b6961390a7d22fa58c2c619a7526def1ca4f365234157a02e614e` |

Verified blockers:

1. The pinctrl log explicitly rejects `nvidia,pull` on LCD mux group `ld0`. All 31 LCD mux groups in this driver lack per-signal pull registers; six separate shared pull groups own those register fields. The copied legacy per-signal properties were therefore invalid for this driver. The initial compiled-DT checks did not cover this capability mismatch. Patch 0048 corrects the mapping; the new cross-check uses the actual pinned pinctrl table and rejects the failed image28 DT.
2. The scoped LP8550 probe returns `-EINVAL` from its production-register verification and does not bind. RGB/panel probe consequently remains deferred (`-EPROBE_DEFER`); no fb0 exists after the bounded 15-second wait. The first mismatch was not logged, so the specific register/value and its cause remain unknown. It is not evidence of failed I2C transfer or proof that the pinctrl failure caused the mismatch. Patch 0049 logs the fixed A1–A7 values and expected values, preserving the no-write-on-mismatch rule.

Additional verified progress: 16 MiB CMA reserved successfully; host1x clock is enabled and PLL_C/disp1 report 598,000,000 Hz. These enable counts/rates are not proof of an active pixel stream. The operator answered the handoff prompts but did not give a screen description; do not invent one.

The existing UP/two-CPU-DT warning and sysfs attribute permission warning remain, as in earlier successful diagnostic images. Do not conflate them with the explicit display errors.

The original boot image was restored. Complete boot and recovery readbacks match their preserved originals, with a completed original Android boot and unchanged boot ID during verification. No recovery write, repartition, Android filesystem write, arbitrary MMIO or EEPROM programming occurred.

Next image29 keeps USB/storage, timing, clock, current limits and diagnostic transport unchanged. It corrects shared pull groups, improves rejected-register evidence and changes the trace cookie only. It must pass actual pinctrl capability checks before testing. The backlight guard will not be weakened to obtain a visible image.

See [image28 preparation](trace-boot-attempt-28-prepared.md) for image/layout hashes, host tests and the lockscreen integration route.
