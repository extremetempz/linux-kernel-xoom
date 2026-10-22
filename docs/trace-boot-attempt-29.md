# Image 29: first visible Linux 4.4 display

22 October 2026. **Visible RGB scanout passed.** The operator reported “i see rgb on the screen”. Two independent fresh USB reports confirm the draw program completed successfully, the framebuffer/connector/backlight state and retained full eMMC/BigPart geometry. This is the real diagnostic color-bar pattern, not Android or a lockscreen.

| Capture | Bytes | SHA-256 | DC interrupt count |
| --- | ---: | --- | ---: |
| 1 | 52612 | `df3c9e58071cafcacdff595fdeb8bf804853acb2a2feddd0324d8f02e25ab6e3` | 3959 |
| 2 | 52612 | `a8ca05fd718c8eb364bb3b74c19d2ed36d9bbc25ec49464f682e79cd21ebd5b7` | 4978 |

## Verified on hardware

- Linux `4.4.147-wingray-display`, cookie `0x584d001d`, donor `a8a26819`; image SHA-256 `229b8d412106536995744d6c2e8bc3a955f39c6955a44a4ae247566ea9f6a0d6`.
- The once-only pattern starter found fb0 immediately, validated/reapplied its existing mode and returned zero after drawing eight vertical bars.
- fb0 is 1280×800, 32 bits per pixel, stride 5120. LVDS-1 reports connected, enabled, 1280×800 and DPMS On. The fbdev mode string ends in p-0 because the DRM helper deliberately exposes pixclock zero; it is not a measured zero refresh rate.
- PLL_C and disp1 report 598 MHz, the programmed shift divider is 16. The nominal derived pixel clock is approximately 66.444 MHz. No oscilloscope pixel-clock or refresh-rate measurement was made.
- The bound P3 backlight reports brightness 128/255, power 0 (unblanked), control 01=03 and A0=5C (92), matching the capped production current policy. Identity is FC and every A1–A7 production byte matches. No EEPROM settings were rewritten.
- DC interrupt count increases from 3959 to 4978 across the reports. This is activity evidence, not proof of underflow-free sustained scanout or an independently measured frame rate.
- GPIO PB2 remains owned output-high. The regulator exposes nominal 5,000,000 µV and num_users 0; do not infer electrical voltage or consumer-reference counts from that metadata alone.
- USB reports pass independent nonce/length/SHA-256 validation after close/reopen. Whole disk is 62,521,344 sectors and all ten BigPart start/size pairs match the fresh original-kernel reference. No Android block filesystem is mounted.

## Diagnosis and limits

The image28 unsupported-pull error disappears after moving pulls from 31 mux-only signal groups to six real shared pull groups. New checks compare against the actual Tegra20 capability table and reject the old DT. The initial RGB EPROBE_DEFER messages in image29 are transient; the panel/backlight dependencies subsequently bind and DRM/fb0 initialize. Do not label those resolved deferrals as a final display failure.

The backlight production guard remains unchanged and now passes. Image28 did not log the mismatching byte. Image29 changed both pin configuration and register logging/timing, so the precise cause of image28’s LP8550 mismatch is not isolated. One successful warm-boot cycle does not prove cold-boot/repeated-boot robustness.

The prior CPU-DT and sysfs-permission warnings remain separate from display success. Touch, Android init/framework, the legacy NVIDIA interfaces, software EGL integration, power management and other peripherals are not validated by this result.

## Preservation and next gate

Original boot was restored after capture. Both complete boot and recovery readbacks match their preserved originals; original Android completed boot and stayed in the same boot during verification. No recovery write, repartition, Android filesystem write or reserved-RAM retrieval occurred. No device test or serial watcher remains active.

The next gate is Android userspace compatibility, keeping this tested display DT/current policy and USB evidence. Inspect the installed Android4.4.4 ABI and init, enable only its required kernel services, reconcile graphics allocation/EGL and device paths, and use read-only system plus RAM-backed first-boot data where possible. A real lockscreen requires framework startup; do not substitute a drawn image or call diagnostic userspace Android.

See [image29 preparation](trace-boot-attempt-29-prepared.md), [image28 failure](trace-boot-attempt-28.md) and [Android startup gates](android-boot-gates.md).
