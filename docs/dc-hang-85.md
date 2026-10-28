# Candidate 85 — manually armed DC hang localization

**Later hardware result:** [one observed DC cycle passes](dc-hang-85-result.md).
The following is the original preparation record; its no-flash statements
refer to development before that separately authorized test.

28 October 2026. Based on main `8447ed0`, following the two corrected-console
warm-reset passes in [candidate 84](suspend-retention-84-result.md).
**Built and checked offline. Not flashed; no DC cycle, reboot or suspend
was initiated during this development. Candidate 84 remains on the tablet.**

## Diagnosis so far

The full IRQ/candidate-81 DC combination lost display wake and USB. The
isolated IRQ/backlight path passes. Candidate81's native reference timing,
all-window restoration and flip serialization are retained. There is still
no recovered failure trace identifying the blocking operation. This image
localizes that failure; it does not claim to fix it.

Reviewed call path: Android lights adapter -> fb0 blank ->
`tegra_fb_wingray_dc_blank()` -> legacy flip lock -> backlight update ->
DC lock -> RGB/IRQ/bandwidth/clock/panel shutdown -> host idle. Resume goes
through host busy, panel/clock/reset/IRQ initialization, RGB activation,
all-window restore and bounded window synchronization before backlight on.
Potentially blocking boundaries are distinguishable without adding register
reads while DC is off. Source inspection alone cannot identify the hardware
stop or prove a deadlock, clock fault or IRQ storm.

## Changes

- Patch **0157** adds `wingray_android44_wakeirqdc_defconfig` and optional
  `CONFIG_FB_TEGRA_WINGRAY_DC_TRACE_TEST`. The appended ECC DT is **identical
  to candidate 84**. No reservation, timing, regulator, pinmux, clock policy,
  IRQ wiring, EMC voltage/rate policy or charging setting changes.
- The image boots with **backlight-only** blanking. Root-only sysfs control
  `/sys/class/graphics/fb0/wingray_dc_test` starts at zero. Its setter uses
  `info->lock` then `legacy_lock`, checks live/healthy flip ownership and
  enabled/nonblanked DC, and refuses both arm and disarm while DC is off.
  Failure to publish this control leaves the gate closed. A reboot clears it.
- Process-context `WG_DC85` console checkpoints surround work draining,
  mutex acquisition, backlight update, DC enable/disable, RGB callbacks,
  IRQ masking/draining, bandwidth clearing, clock operations, panel handling,
  syncpoint flushing, host busy/idle, window restore and sync. Each records
  phase, PID, software enabled state and a return/status value.
  The helper samples no hardware registers or clock providers and takes no
  new locks. It does not log from IRQ context. Framebuffer console/VT are off
  in the built profile, avoiding console rendering through the DC being tested.
  Checkpoint timing can still affect reproduction; this is not a timing-neutral
  observer or a guaranteed last-instruction trace.
- Patch **0158** keeps negative errors signed in the gate's sysfs return.
- Fixed USB command **DCTEST** invokes the existing framebuffer test with
  its fixed `--dc` argument. It requires the new root-only gate to be present
  and initially off, arms it, performs one blank/unblank cycle, then disarms.
  Normal **FBTEST** never arms DC. Neither boot nor ordinary REPORT/PSTORE
  runs DCTEST. USB input remains a nonce-checked fixed request, never shell.
- Host `run-fb-blank-test.py --dc` explicitly selects DCTEST. A verified frame
  is separate from `dc_commands_completed`; physical display success still
  needs observation. A kernel hard hang cannot be recovered by a shell trap
  or a host timeout. No automatic reset, panic, restore or rail toggle is added.

The checkpoint helper compiles to no-ops in the existing profiles. Existing
candidate84 artifacts and original boot/recovery backups remain untouched.
The same ECC record format is required for post-hang log recovery. PM,
SUSPEND, autosleep and DVFS stay disabled.

## Build identity and checks

Apply the series through **0158** before selecting `wakeirqdc`:

```sh
XOOM_ANDROID_GPU_PROFILE=wakeirqdc \
XOOM_BUILD_ROOT=/tmp/xoom-dc85-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/dc85-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/dc85-new-ready" \
bash scripts/build-android-gpu.sh
```

Prepared local image: `artifacts/dc85-ready-final/wingray-android44-gpu.img`.
Size **4,155,392 bytes**. SHA-256:
`168a49a18144cd98bccc8cc1045b97897b8709533bd85e424303452dd9c1cc0c`.
Kernel source head `59835aa5` (checkpoint commit `281223a0`). The full ARM
kernel/module/runtime/image build passed, followed by the signed-return
correction's rebuild/repack. The latter generated the same image hash.
The linked runtime and all manifest source hashes match.

Passed offline: actual native-mode/all-window callbacks and failure rollback,
20 software DC cycles, backlight-only callback regressions, actual manual gate
lock ordering/invalid/poisoned/dead/off-state controls, actual fixed shell
arm/restore/disarm and missing/already-armed controls, CPCAP ON handler,
compiled display/ECC/IRQ/config/reservation checks, generic framed-report
regressions, pstore framing/retention/ECC tests. Synthetic tests do not prove
physical scanout, hard-hang recovery or a working DC cycle on this image.

## Later operator-controlled hardware test

No flash or test command below was executed by this work.

1. Preserve candidate84, Test5/IRQ-backlight rollback and complete original
   boot/recovery images plus hashes. After separate authorization, flash
   **boot only**, start candidate85 and verify Welcome/USB, gate `0`, ECC
   backend binding and a fresh normal/PSTORE baseline. Do not press the
   physical power button during the fixed test, to avoid interleaved requests.
2. Issue exactly one explicit test:

   ```sh
   python3 scripts/run-fb-blank-test.py --dc \
     --output-dir artifacts/dc85-cycle1
   ```

   If it returns, require arm acknowledged, both blank writes successful,
   disarm successful and gate zero. Observe actual darkness and restoration
   of the same session without a scan line. Capture normal and PSTORE reports.
   Command completion alone does not establish physical display success.
3. If USB/display hangs, stop sending tests. Use the established physical
   manual warm-reset method into **the same installed image**. Its gate is
   zero again, so Android should take the backlight-only path during recovery.
   Recovery after a DC hard hang is still unverified: if it cannot boot, use
   operator-controlled fastboot boot-only restoration of candidate84, which
   has the same ECC DT/record geometry. Do not boot the original 2.6.39 image
   first, because its legacy logger may overwrite evidence.
4. Reconnect USB and capture PSTORE into a new private directory. Check the
   ECC footer, complete capture and old-console identity before interpreting
   `WG_DC85` lines. Unrecoverable blocks, missing lines or a truncated tail
   limit the verdict. Preserve raw captures privately. Do not delete records.

Useful checkpoints include `fb.lock.wait/acquired`, `disable.lock.begin/end`,
`disable.irq.begin/end`, `bandwidth.clear.begin/end`, `clock.disable.begin/end`,
`host.idle.begin/end`, `enable.lock.begin/end`, `clock.setup.begin/end`,
`controller.init.begin/end`, `fb.windows.begin/end`, `fb.sync.begin/end`,
`fb.rollback.begin/end` and `fb.exit`. Keep PID, order and returned values.
A begin without its end narrows an operation interval; it is not by itself
proof of why that operation stopped, especially with corrected/missing data
or concurrent workers.

Only after that evidence should a separate causal correction be made and
tested. Do not enable system suspend, LP0/LP1/LP2, new regulators or voltages
as part of this diagnostic. No power savings are claimed.
