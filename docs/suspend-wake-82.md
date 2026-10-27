# Suspend preparation 82 — IRQ-only power-key prerequisite

27 October 2026. Based on latest main `af84f7c`, including the candidate 81
hardware result and corrected patch 0151. **No flash, reboot, suspend attempt,
live ADB access, regulator/charger change or voltage change was performed.**

This is the first required suspend prerequisite, **not a working deep-sleep
image**. Candidate 81's native timing, all-window restore and flip exclusion
remain enabled. Original boot/recovery, candidate 81 and Test 5 are preserved.

## Why suspend cannot simply be switched on

The validated key currently samples CPCAP INTS registers every 20 ms. That
worker cannot execute while the CPU is suspended. Its setup unmasks ON
directly in INTM2, but no nested ON consumer updates regmap-irq's software
mask. `regmap_irq_thread()` filters pending status through that cached mask.
Thus a physically unmasked ON latch can be ignored. This is a concrete
ownership mismatch consistent with the existing storm/disabled parent;
hardware evidence must establish whether it explains the complete storm.

The current DT additionally routes CPCAP directly to the GIC. Tegra LIC's
`irq_set_wake` owns the low-power interrupt mask; bypassing it is not a valid
wake configuration. The Linux IRQ number (previously 59) is dynamic. The
hardware source stays **GIC SPI 86, level high**, matching original
INT_EXTERNAL_PMU; no GPIO or IRQ number is guessed.

There is a second independent blocker: the fixed-clock nvhost GPU experiment
depends on `!SUSPEND`. Enabling CONFIG_SUSPEND silently removes the tested GPU
configuration. That guard must be replaced by a separately reviewed PM
integration, not deleted to make the configuration appear to build.

## Implemented in patch 0152

- Separate `wingray_android44_wakeirq_defconfig`, based on the corrected
  displaydc config; PM/SUSPEND/DVFS stay off.
- Separate wakeirq DT includes the unchanged display/battery/radio stack.
  Only CPCAP's interrupt parent changes to the existing Tegra LIC, with an
  explicit test marker. Physical interrupt cells, SPI2/CS-high/native32,
  10 MHz limit, pinmux and all rails/timings are unchanged.
- Register ON from **irqdata[2]**, the normal INT1–4 domain, relative index
  **23** (INT2 bit 7). Macro domains 0/1 are not the ON domain.
- Request the nested threaded IRQ so regmap owns its mask and W1C ACK. Clear
  only stale ON before registration and check INTM2 readback after request.
  No direct runtime unmask behind the mask cache, global ACK, parent IRQ
  suppression or polling fallback is added.
- Preserve press/release and held-button state. Reuse Motorola's original
  quick-click policy when a whole press/release completed before the threaded
  sense read. Failed sense reads report errors without inventing key state.
- Check LIC routing and propagate setup/transport errors. A failed IRQ test
  cannot quietly register the old poller and be mistaken for working IRQs.
- Add read-only `wingray_irq_status` on the CPCAP SPI device. It reports
  parent chip/hwirq, nested IRQ/index, event/error counters and INT/INTM/INTS
  for all four normal banks, including unmasked-pending bits. The normal
  diagnostic power report reads it; there is no periodic diagnostic poll.
- Preserve existing displaypm/displaydc/battery behaviour unless the new
  config **and** DT marker are selected. Baseline profiles still use their
  previously tested polling path.

The handler includes a wakeup-event notification for a future PM-enabled
integration, but this build has PM_SLEEP disabled. It **does not arm a wake
IRQ, expose a new sleep state or prove that the power key wakes the SoC**.
The previous unchecked parent `enable_irq_wake()` call is skipped in this
test; a future PM profile must check actual wake arming and errors.

## Build, offline evidence and identity

On a fresh source checkout, apply the numbered patches through 0152 before
building. The ignored local donor is not distributed as source in this repo:

```sh
python3 scripts/fetch-sources.py
python3 scripts/apply-kernel-patches.py
XOOM_ANDROID_GPU_PROFILE=wakeirq \
XOOM_BUILD_ROOT=/tmp/xoom-wake82-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/wake82-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/wake82-new-ready" \
bash scripts/build-android-gpu.sh
```

Build checks now fail if Kconfig drops the DC or IRQ test symbols. A missing
0151/0152 cannot silently produce a different test image. Do not reapply the
whole series blindly to an already patched local donor.

Prepared locally: `artifacts/wake82-final-ready/wingray-android44-gpu.img`.
4,147,200 bytes; SHA256:
`c0a7f7b6091db710f36e276820f31d25aaefe4c6f6bf207953ec9d3561454f22`.
Full ARM kernel/DT/module/runtime/image build and linked archive checks pass.
The image manifest identifies `android44-wakeirq`, IRQ-only testing and
`hardware_wake_validated=false`, `soc_suspend_enabled=false`.

Tests execute the actual registration and key-handler functions with faulted
regmap operations: correct domain/index; LIC rejection; initial held key;
50 software press/hold/release sequences; quick clicks; failed reads, stale
ACK, IRQ request, mask readback and registration. Compiled DT/config checks
reject PM, suspend, voltage-regulator or SPI drift and missing test symbols.
Existing native-mode/window, CPCAP transport, battery, Bluetooth and display
scope checks pass. These are software checks, not hardware IRQ validation.

Preserved images:

- Hardware-tested candidate 81: `e02c7c41f5e95ed3f8155ce7d1761e355b98b0df4931fec7cedf08f2c71dc1ea`.
- Test 5 backlight-only: `02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`.

## Required next hardware test — awake only, no automatic execution

After separate operator authorization and normal backup/power/restore checks:

1. Boot the IRQ-only image and collect a fresh framed report. Expect
   `Wingray ON IRQ-only registered`, `chip=LIC`, `on_domain_index=23`,
   `polling=0`, no sense errors and ON clear in the INTM2 mask readback.
   Do not require Linux IRQ 59; inspect the reported mapped numbers.
2. Record counters at idle and after deliberate power-key presses. Verify
   genuine nested ON IRQ counts and matching Android input. Test short,
   long and repeated presses/releases. No phantom/repeating input is allowed.
3. Inspect all unmasked-pending banks and `/proc/interrupts`. Any `nobody
   cared`, disabled parent, continuously increasing idle count or SPI error
   is a failed test. Save evidence and restore candidate 81; do not hide a
   storm by disabling the parent or clearing every PMIC latch.
4. Repeat Android display/DC cycles and verify GPU, touch, Wi-Fi, Bluetooth
   and battery/charger readings. Capture reports before/after the input test.
5. This still proves awake IRQ delivery only. Real wake arming and wake from
   a controlled platform state require the later PM test below.

The test makes no charger-control, shared Wi-Fi/BT rail or persistent-data
changes. It does not modify original boot/recovery. On failure use the
established physical fastboot sequence and authorized boot-only restoration
to the preserved candidate 81 or Test 5 image; verify boot/recovery hashes.

## Follow-on implementation gates

1. **PM framework and devices, still no platform power-down:** after the IRQ
   test passes, introduce a separate PM/debug profile and an explicit GPU PM
   compatibility gate. Keep platform ops unregistered and autosuspend off.
   Inspect the actual Android libsuspend backend/wakelocks. Use staged
   freezer/devices/CPU tests with rollback, not an immediate `mem` write.
2. **Hardware wake arming:** register and arm the correct interrupt path
   through LIC, check return/readback/pending status, preserve CPCAP transport
   and SPI-controller resume ordering. The old regmap wake API queues parent
   wake operations without propagating their errors; an unchecked nested
   enable return is not sufficient evidence.
3. **Device callbacks:** drain GPU submissions and preserve host/syncpoint/
   nvmap/DC state; pause battery polling and safely restore OWR clocks and
   timings; retain hardware charging; handle touch slots/scanning; validate
   SDIO KEEP_POWER/reconnect, Bluetooth UART/host-wake and shared rail votes;
   restore USB, timers and eMMC. Display-only resume is not all-device resume.
4. **CPU/cache:** test CPU1 offline/online separately, then CPU/cluster PM,
   PL310 context and local timers. Existing Tegra20 CAR suspend/resume hooks
   exist; initial SMP boot does not validate those hooks.
5. **Controlled LP2:** only after the above gates, use original Motorola
   power-handshake parameters and a recoverable physical power-key test.
   LP2 stops/power-gates the CPU complex but keeps DRAM active; it is not
   DRAM-self-refresh deep sleep. Record actual platform entry/return and
   errors, rather than treating `/sys/power/state` or a black screen as proof.
6. **LP1 / genuine retained-memory sleep:** only after reliable LP2 and
   repeated device recovery, verify IRAM reservations, reset trampoline,
   EMC/DRAM self-refresh and board retention. LP0 needs a separate validated
   warmboot vector and complete PMC wake/power sequence; it remains excluded.
7. **Android automatic suspend and energy:** honour active wakelocks, retain
   one validated autosuspend backend, then test 20 cycles and progressively
   longer sleep. Measure DS2781 charge/current before/after or use external
   power; do not fabricate a current reading while the CPU is asleep.

Actual suspend-to-RAM and deep sleep remain unimplemented/unvalidated in
this delivery. The next actionable gate is a real ON IRQ test, not a voltage,
LP0, charger or Samsung board-code experiment.
