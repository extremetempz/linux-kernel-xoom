# Suspend prep 82 — isolated IRQ + backlight-only test

**Updated result:** [IRQ/backlight-only passed on hardware](suspend-wake-82-backlight-result.md).
The PSTORE command was available, but its backend was unbound and its VFS
was not explicitly mounted by this RAM runtime. The historical recovery
procedure below cannot recover the lost combined-profile log. Use the
[separate retained-console validation](suspend-trace-83.md) before relying
on pstore; Test 5 and original Android are not matched ramoops recovery images.

27 October 2026. This is a new experimental profile after the full wakeirq
profile failed: screen-off lost wake and the USB gadget, with no log.

It isolates the two variables:

- **IRQ-only CPCAP ON path** — same as suspend prep 82.
- **Backlight-only display path** — no candidate 81 DC power-down.
- PM, PM_SLEEP, SUSPEND, wake arming and DVFS remain disabled.
- A fixed read-only `PSTORE` USB request captures `/sys/fs/pstore`,
  `/proc/last_kmsg` if present, and the current dmesg tail.

Image:

- `artifacts/wakeirqbl-review-ready/wingray-android44-gpu.img`
- 4,147,200 bytes
- SHA-256 `7219443f7bfa2caf6be935ecb08162e7c05ef7e3988e5bf385890ecb07317f09`
- manifest: `cpcap_irq_only_test=true`,
  `dc_resume_experimental=false`, `power_key_polling=false`,
  `hardware_wake_validated=false`, `soc_suspend_enabled=false`

Offline tests pass: ON handler/registration, backlight-only fb callbacks,
profile/DT isolation, pstore request, battery/CPCAP/Bluetooth/Wi-Fi and the
inherited display software tests. No hardware IRQ or wake test has been run.

## Test with pstore fallback

Do this only after preserving Test 5 and a fastboot recovery path. Do not
attempt suspend.

1. Before any screen-off test, take a pstore snapshot:

```sh
python3 scripts/run-pstore-report.py \
  --output-dir artifacts/wakeirqbl-pstore-before
```

2. Long-press the power button to open the power menu, dismiss it, and take
   another pstore snapshot. This tests IRQ delivery with the display awake.
3. Only if that passes, short-press once to turn the screen off. Capture a
   normal framed report while the screen is off:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/wakeirqbl-off \
  --storage-mode android44-readonly
```

4. Press power again. If it wakes, capture `wakeirqbl-after`.
5. **If it hangs**, force power off and boot Test 5. After the next boot, run
   `scripts/run-pstore-report.py` first; ramoops may contain the failed boot.

## Interpretation and rollback

If the display stays dark but pstore/IRQ counters show the ON event, the IRQ
path works and the display path is the remaining problem. If pstore shows a
hang before the ON handler, the IRQ registration/LIC path is implicated. No
root cause is claimed until a log exists.

Test 5 remains the conservative rollback:

`artifacts/display80fbtest5-ready/wingray-android44-gpu.img`
SHA-256 `02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`.

Do not enable PM or suspend with this image.
