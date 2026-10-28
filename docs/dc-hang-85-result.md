# Candidate85 — ten instrumented IRQ/DC cycles complete

28 October 2026. Exact image from [candidate85 preparation](dc-hang-85.md),
SHA-256 `168a49a18144cd98bccc8cc1045b97897b8709533bd85e424303452dd9c1cc0c`,
4,155,392 bytes; kernel source `59835aa5`.

## Deployment and baseline

The operator explicitly authorized flashing and fastboot identified Xoom Wi-Fi.
Transfer, boot write and reboot returned success. Only boot was flashed;
recovery and partition layout were untouched. Original boot/recovery backup
files passed their recorded checksums before flashing. No live partition
readback is claimed. Candidate85 remains installed; the original boot image
has not been restored after this test.

A verified fresh REPORT confirmed Android boot completion, SurfaceFlinger/
zygote, CPUs 0–1 and matching full eMMC/ten-BigPart-partition geometry under
the read-only-system/RAM-data policy. PSTORE confirmed ECC16, backend binding
and the same reserved-memory/record layout. Android initially reported screen
asleep, brightness zero; the operator woke it before the fixed experiment.

## One manually armed DC test

The nonce-checked DCTEST request completed and its complete 13,053-byte
payload hash matched. It checked the gate was zero before arming. Results:

```text
DCTEST_ARMED_1
FB_BLANK_WRITE4_RC 0
FB_BLANK_WRITE0_RC 0
DCTEST_DISARM_RC 0
DCTEST_ARMED_AFTER 0
```

Checkpoints show disable IRQ drain, bandwidth clearing, clock disable,
panel callback, syncpoint flush and host idle all returned. Software DC state
reached zero. Resume returned through host busy, panel/clock/reset/IRQ setup,
controller initialization, RGB activation and all-window restoration.
The existing scanout readback reported:

```text
Wingray DC test scanout: ref=0001000b command=00000020 clock=00000000 restored=5 sync=99
Wingray DC test on: dc=1 restored=5 sync=99 href=11 vref=1
```

The positive sync result is remaining timeout, not an error. Backlight-on
returned zero, fb exit returned zero, and post-test gate checkpoints confirm
disarm. The exit trap's additional disarm is expected.

The operator explicitly confirmed complete darkness during blank, return
without a scan line, and working touch. The host's machine-generated
`visible_display_validated=false` means that script cannot observe the panel;
this separate operator report supplies physical confirmation. Raw machine
status was preserved unchanged.

A fresh post-test REPORT again passed integrity and storage checks:
`sys.boot_completed=1`, CPUs 0–1, backlight brightness/actual brightness 102,
bl_power 0, CPCAP IRQ-only polling=0, events=8, errors=0. Before/after PSTORE
show the same boot ID, so no reboot occurred. These same-boot snapshots do
not test retention after a hard hang. The startup sysfs-group warning at
0.948566 seconds was already present in the pre-test baseline; it was not
caused by this cycle. No absence of all unrelated warnings is claimed.

## Repeated-cycle follow-up

After a fresh verified REPORT, the operator woke the screen and approved
nine more fixed DCTEST cycles (cycles2–10), with immediate stop on any
command failure. All nine returned verified frames, successful off/on and
disarm writes, gate zero and native href11/vref1 restoration with a positive
window-sync result. The operator reported “looks good!” during this batch.
Combined with cycle1, ten instrumented cycles completed without a reset.
The ten saved payload sizes/hashes and required result markers were
independently rechecked.

The post-cycle10 REPORT again confirms Android boot completion, awake state,
CPUs0–1, matching full disk/BigPart geometry, polling=0 and CPCAP events18,
errors0. Private follow-up captures are `dc85-repeat-before`, `dc85-cycle2`
through `dc85-cycle10`, and `dc85-after-cycle10`. No further image was flashed.

## Accepted scope and limits

**Ten instrumented combined IRQ/DC cycles completed.** Cycle1 has explicit
complete-darkness/no-scan-line/touch confirmation; the follow-up batch has
the operator’s positive visual observation and verified command results. The old hang did not reproduce. Its
cause remains unknown; checkpoint timing may affect reproduction. This is
not a causal fix, long-duration reliability qualification, system PM callback test,
low-power wake test or deep-sleep result. No new Wi-Fi/Bluetooth reconnect,
GPU stress, charging-control or power-consumption test was performed.

The manual DC gate is zero again. Normal power-button blanking uses the
backlight-only path. System suspend remains disabled. Next: checked CPCAP wake arming and
Motorola system-PM restoration work; retain the preparation86 sleep-entry
block until those dependencies are addressed.

Private reports remain in ignored artifacts under the dc-hang-85 workspace:
`dc85-baseline`, `dc85-pstore-before`, `dc85-cycle1`, `dc85-after-cycle1`,
`dc85-pstore-after-cycle1`, and `dc85-deployment`. All five captured payloads
were rechecked against saved lengths/hashes and nonce-bearing wire captures.
No raw logs, serial identifiers or original ROM contents are uploaded here.
