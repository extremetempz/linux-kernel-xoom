# Image 31 — first completed Android boot on the ported Linux 4.4 kernel

Tested 22 October 2026. **Android 4.4.4 completed startup and displayed the real
Welcome screen.** Both boot-completion properties were `1` in two independently
verified reports, with SystemUI running. The operator confirmed the screen.
This is an Android userspace boot milestone; it is not a completed hardware
port or a demonstrated lockscreen.

Original restoration: **complete boot and recovery readbacks match their
preserved originals, Android startup is complete, and the working ROM is running.**
Recovery and the partition layout were not written.

## Image and change

- Image: 3,481,600 bytes, SHA-256
  `f4b529fb8b31d99d741830690bc332b48db46ab3900423986d85eb76f04b8b43`.
- Kernel is byte-identical to image 30: source `400dbc8e`, Linux
  `4.4.147-wingray-android44`, boot-trace cookie `0x584d001e`.
- RAM-disk correction: create `/dev/input` mode 0755, root:input in Android's
  `on init` action, after original init replaces `/dev` and before services start.
  No touchscreen/input driver, fake event node or uinput device was added.
- Read-only reporting now records whether that directory actually exists.

This directly addresses image 30's observed EventHub constructor assertion.
The host regression reproduces its ENOENT using real inotify and then accepts
an empty temporary directory. Physical reports confirm the generated directory
exists with the expected ownership/mode; image 30's EventHub abort is absent.

## Physical evidence

| Report | Bytes | SHA-256 | Android completion |
|---|---:|---|---|
| 1 | 87,473 | `46d31a6323215c4176aca5bee9a88d2afbe786b6ffc4435b1caf3dafbc6135bf` | Initial package scan |
| 2 | 92,591 | `c779d924fb9bd0529f62f9dbaf0153cb2c13637c97e7003ec89f59a19a670c14` | Both flags 1, SystemUI present |
| 3 | 96,407 | `7750cc4687d5a75ccfd6cd6f107a7af39e5c61f3085890b08937048122bb3fd2` | Both flags 1, SystemUI present |

Each report passed nonce, byte-count and SHA verification. All retained the
full 62521344-sector capacity, all ten BigPart extents, eleven eMMC RO flags,
fixed system mount with journal replay disabled, fresh RAM data/cache and both
read-only RAM graphics overlays. Native ABI and fixed system-reference checks
passed. No original userdata or cache partition was mounted.

Android's display manager reported the built-in 1280x800 display. Logs showed
the package scan progress, `Displayed com.google.android.setupwizard/.WelcomeActivity`,
and SurfaceFlinger's `Boot is finished (92912 ms)`. That log duration is not an
independent cold-boot performance measurement. The operator observed Motorola
logo, RGB bars, blank screen during initialization, then Welcome.

## Limits and next work

Touch does not work in this profile because input and touchscreen drivers remain
disabled. Creating EventHub's directory permits framework startup; it does not
implement touch. The Welcome screen is expected with unprovisioned RAM-backed
data. Current installed userdata and its lockscreen configuration were not used.

Next isolate the real touchscreen's board power/reset/interrupt wiring and
driver, validate genuine events, then complete RAM-only setup/provisioning toward
the real lockscreen. Keep the known-booting kernel/profile as the control. Do not
enable unrelated PMIC, GPU or suspend code merely to obtain input.

This is one warm hardware boot. Cold/repeated boot robustness, touch, Wi-Fi,
sound, sensors, cameras, battery/charging policy, GPU acceleration, suspend and a
newer Android ROM remain unvalidated. Raw logs, tombstones, complete images and
readbacks are private under ignored `artifacts/android44-image-31-ready/`.
