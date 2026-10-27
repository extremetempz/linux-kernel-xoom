# DC resume candidate 81 — hardware-validated display resume

Reviewed main `13c2ff4`, especially `d79b516`, `7373da6`, `e257af5` and
the private FBTEST3/Test 5 reports. Test 5 remains the accepted backlight-only
baseline; candidate 81 does not replace it. No device operations were run.

## What actually failed

The old path logged `dc=0` then `dc=1`, but the panel stayed dark with a scan
line. A successful enable boolean and positive window-sync return were not
proof of a correct panel signal or visible scanout. Rolling back was sound.

Three source-level defects/limitations are now addressed in **opt-in** patch
0151, after the validated backlight-only patch 0150:

1. **Cached mode drift.** The working boot DT supplies href=11, vref=1,
   pclk=66400000. The FBTEST3 boot log later says `Using mode ...
   pclk=66401000 href=0 vref=1`. `tegra_dc_set_fb_mode()` round-trips through
   fb_videomode, which has no Tegra ref-to-sync fields, and calculates new
   references. It updates the cached mode without programming the active DC.
   On re-enable, `tegra_dc_init()` programs that changed cache. Candidate 81
   accepts only the fixed RGB native mode and retains the entire DT mode,
   including its reference timing and flags, without inventing new timings.
2. **Incomplete window restoration.** `_tegra_dc_controller_disable()` clears
   ENABLED on every window. The previous resume enabled only `fb->win`, not
   every window used by the proprietary compositor. Candidate 81 saves all
   window flags and restores all three windows, preserving their existing
   addresses, strides, formats, geometry and pinned front-buffer ownership.
   It does not force an inactive fbdev window on.
3. **Flip serialization.** The earlier callback did not hold `legacy_lock`
   against synchronous legacy Android flips. Candidate 81 takes that lock
   across the transition and rejects new flips with EBUSY while DC is off,
   before pinning buffers or publishing a completion syncpoint. This avoids
   falsely completing an off-state flip or poisoning it through a timeout.

These are verified software mismatches. They are **not proof of the unique
physical cause** of the scan line, nor a claim that candidate 81 resumes on
hardware. HWC handling of off-state EBUSY also needs the staged test below.

## Motorola comparison

Original [board-stingray-panel.c](https://github.com/Schischu/android_kernel_moto_wingray/blob/jb-mr2/arch/arm/mach-tegra/board-stingray-panel.c)
defines the native 1280x800 mode, shared active-high panel supply and 200 ms
startup delay. The rail also feeds touch/backlight/I2C dependencies. The old
[DC implementation](https://github.com/Schischu/android_kernel_moto_wingray/blob/jb-mr2/drivers/video/tegra/dc/dc.c)
does not clear window flags as this donor does. The original
[framebuffer code](https://github.com/Schischu/android_kernel_moto_wingray/blob/jb-mr2/drivers/video/tegra/fb.c)
also constructs a cached mode with reference values of 1; therefore do not
claim the original kernel always preserved href=11. Candidate 81 instead
preserves this port's proven initial native mode to remove that transition
variable. The donor's existing reset/clock/RGB programming is reused.

No Samsung regulator, pinmux or panel sequence is imported. No shared rail
is forcibly switched, no GPIO is toggled and no speculative panel-reset delay
is added. Clock/voltage optimisation and system suspend remain disabled.

## Safe error handling and diagnostics

Backlight off must succeed before DC shutdown. Resume re-enables DC, restores
all windows and waits for scanout synchronization before lighting the panel.
The owner reads REF_TO_SYNC, DISPLAY_COMMAND and DISP_CLOCK_CONTROL only with
DC enabled. A timing readback mismatch or update/sync/backlight failure leaves
the display dark, DC disabled, saved flags and buffer pins retained for retry.
It does not restart Android or release scanout memory prematurely.

Expected diagnostic lines:

```
Wingray native mode retained: href=11 vref=1 pclk=66400000
Wingray DC test off: dc=0 saved=<mask> href=11 vref=1
Wingray DC test scanout: ref=0001000b command=... clock=... restored=<mask> sync=<positive>
Wingray DC test on: dc=1 restored=<same mask> sync=<positive> href=11 vref=1
```

These logs prove only the recorded software/register state. An operator must
confirm the actual image, absence of a scan line and ongoing GPU/touch use.

## Build and offline result

Use the separate selector; normal `displaypm` retains Test 5 behaviour:

```sh
XOOM_ANDROID_GPU_PROFILE=displaydc \
XOOM_BUILD_ROOT=/tmp/xoom-dc81-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/dc81-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/dc81-new-ready" \
bash scripts/build-android-gpu.sh
```

Reviewed build: `artifacts/dc81-review-ready/wingray-android44-gpu.img`.
Size 4,147,200 bytes. SHA256:
`e02c7c41f5e95ed3f8155ce7d1761e355b98b0df4931fec7cedf08f2c71dc1ea`.
Kernel source includes patch 0151 with the duplicate `CONFIG_SUSPEND` line
removed; the documented `70bb707d…` hash was not reproducible as merged.
The runtime contains the final diagnostics and matched built-in archive.

Passed: full ARM zImage/DT/module/runtime/image build; inherited GPU/DT gates;
compiled display/battery/Bluetooth scope checks; native Lights HAL and fixed
FBTEST tests; CPCAP transport/key and DS2781/monitor tests. The existing
displaypm control's fb.o/mode.o also compile with the experiment disabled.

New tests execute the real mode and DC callbacks with UBSan: native-mode
round trip versus the old href=0 result; all-window restoration with window 0
inactive; 20 software cycles; repeated blank; failed light-off, enable, window
update, timeout, interrupted sync, register readback and light-on; safe retry.
These are software tests, not physical suspend/display cycles. The old
backlight-only test's calls[8] overflow was corrected and sanitizer-enabled.

The preserved Test 5 image still hashes to
`02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`.
Original boot/recovery inputs were not written. No raw private logs are
published with this change.

## Later hardware acceptance — no automatic flash

1. Preserve original boot/recovery and Test 5 image plus hashes and physical
   fastboot restoration. Any future flash needs the operator's authorization.
2. Start Android and capture a fresh baseline report. Verify native href=11
   before any blank. Test one fixed FBTEST in a quiet, visible session first.
3. Confirm complete darkness and return of the same image with no line. Check
   register readback, identical saved/restored masks and positive sync. If it
   fails, save the report and restore Test 5; do not experiment with rails.
4. Only after that pass, test a real Android power-key cycle. Check HWC/flip
   errors and framework continuity, not just dc=1. Off-state EBUSY must not
   cause a compositor restart or persistent rendering failure.
5. Then perform ten regular/rapid cycles, exercising animation, multitouch,
   Wi-Fi, Bluetooth and battery/charger reporting after restoration. Verify
   brightness retention. Keep the known-good rollback ready throughout.

This is controller shutdown/restore testing while the SoC remains awake.
It does not enable suspend, solve CPCAP hardware wake or prove energy savings.
Do not attempt `mem`, automatic suspend, LP1 or LP0 with this candidate.
