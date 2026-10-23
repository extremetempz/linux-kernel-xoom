# Power, legacy graphics and Android ABI development

23 October 2026. This work continues the image-33 checkpoint. No candidate was
flashed in this stage. The original ROM remains installed and running; the
complete boot/recovery verification after image 33 remains the last physical
restoration result. Existing hardware-tested configurations and DTs were not
changed. New code below is source/host/object-build evidence, not a hardware pass.

## Separate kernel corrections

| Patch | Commit | Concrete change | Verification |
|---|---|---|---|
| 0063 | `952b0d34` | Refresh the local job pointer after nvhost `set_submit` replaces and releases the old job | Actual write-loop test with replacement providers; old source fails for header plus command data in one write |
| 0064 | `cf8fee2c` | Optional Wingray six-word/24-byte write-header decoder translates wait-count/mask into the existing extended-header machinery | Actual parser tests for combined and split writes, short headers, copy failure, wait records, donor 16-byte mode and non-Wingray behavior; ARM object builds in both modes |
| 0065 | `ac2faf2a` | Shared EMC clocks return underlying rate errors, undo failed software votes, attempt aggregate rollback, and apply/remove enabled votes | Actual callbacks with injected request/rollback failures; four old-source negative controls; ARM object build |
| 0066 | `ca20c30c` | Convert a microvolt margin to millivolts before adding it to a millivolt table limit | Actual constants/table compiled: final entry is 1475 mV, previously 101375 mV; ARM object build |
| 0067 | `f8e236d5` | Preserve a PLL programming error even if subsequent parent restoration succeeds; remove advertised overclock entries on Wingray | Actual target-return tests, stock-table cap and unchanged other-board behavior; acquisition/unwind regressions; ARM object build |
| 0068 | `72368936` | Preserve the current EMC rate when no nonzero minimum vote exists, rather than request zero Hz | Zero-vote prepare/removal tests; final ARM object build |

The nvhost defect is established by source ownership: `nvhost_job_realloc`
drops the old job on successful replacement, while the write loop cached that
pointer before parsing the new header. Same-write command/relocation handling
then used the old object. This path is disabled in the hardware-tested profile,
so it does not explain an observed image-33 userspace crash.

The new `TEGRA_GRHOST_WINGRAY_LEGACY_SUBMIT` option **defaults off**, depends on
the legacy Tegra20 host, and chooses the 24-byte format only for the exact
`motorola,wingray` compatible. It never guesses the format from stream length.
The donor 16-byte UAPI declaration and extended ioctl format remain unchanged.
No legacy host, nvmap, GPU or alternate display profile was enabled.

The ARM32 ABI audit still reports 13 matching nvmap requests, matching measured
nvmap sizes and ten matching shared nvhost requests. Its default nvhost header
remains 16 bytes by design. The optional decoder addresses the measured Motorola
six-word stream; neither that decoder nor equal ioctl numbers proves complete
blob compatibility, memory coherency, relocation correctness or GPU execution.

## CPU voltage and memory-clock limits

There is already a reusable voltage driver at
`drivers/staging/tegra/tegra20-dvfs.c`, in addition to the cpufreq driver and shared
EMC clock helper. Its existence removes any reason to start a new voltage driver
without reviewing it. It is **not ready to enable unchanged** on Wingray:

- Its CPU/core frequency and voltage tables are donor choices, including
  overclock entries; they are not approved Motorola operating points.
- Its voltage-update helpers return void and log regulator failures. A clock
  notifier that proceeds after a failed voltage increase needs separate error
  propagation and sequencing work.
- Motorola CPU/MAX8649 and core/AON/CPCAP relationships, regulator bindings,
  ramp behavior and installed-DRAM EMC tables remain unvalidated in this port.
- Fixing the unit error does not approve 1475 mV on this tablet. No such voltage
  was requested by this work.
- The cpufreq target still needs checked EMC transition ordering and complete
  failure restoration. Preserving its PLL error is a bounded correction, not a
  complete transition transaction. The shared helper now exposes errors that
  callers must actually handle.
- Aggregate rollback is attempted and failures are reported; a provider error
  cannot establish that hardware returned to its previous electrical state.

A read-only snapshot from the restored working ElementalX ROM lists eight
frequencies through 1 GHz plus five higher entries. At the separate reads, current
frequency was 1 GHz, minimum 312 MHz and configured maximum 1.4 GHz. The custom
`UV_mV_table` returned thirteen zeroes and is not a usable voltage table.
Regulator sysfs reported MAX8649 enabled at 1,130,000 uV and SW2/SW4 enabled at
1,200,000 uV, with configured constraints 770000–1400000 and
1000000–1450000 uV respectively. These are sequential framework snapshots,
not atomic frequency/voltage pairs, electrical measurements or safe OPPs.
The new Wingray table cap remains the conservative stock 1 GHz ceiling.
No policy, regulator setting or clock was changed on the working ROM.

## EGL, gralloc and hardware composer

Device commit `53dfbe3`, exported as Android patch 0002, extends the existing
Wingray wrapper: valid layer lists now release owned acquire descriptors and
initialize output fence fields on allocation failure, blanking, missing surface
and legacy-HAL error paths. Unrepresentable counts are rejected before unsafe
layer enumeration. The earlier bounds patch remains separate.

Host tests execute the actual prepare/set/cleanup functions with provider
substitutions. Both the original wrapper and the previous bounds-only version
fail the corresponding negative controls. This is not a complete HAL build.

**Remaining integration blocker:** the inherited wrapper does not establish
proper asynchronous acquire/release ordering around the old HAL. Adding a
blocking wait inside `set` would conflict with the Android 4.4 contract; this
stage does not add such a wait or pretend descriptor cleanup resolves ordering.
A matched HAL/framework path must account for unfinished buffer producers and
scanout completion before this wrapper is activated. See the pinned
[Android 4.4 HWC contract](https://android.googlesource.com/platform/hardware/libhardware/+/android-4.4.4_r2/include/hardware/hwcomposer.h)
and [libsync implementation](https://android.googlesource.com/platform/system/core/+/android-4.4.4_r2/libsync/sync.c).
No proprietary libraries were replaced and no EGL/gralloc/GPU path was enabled.
The image-33 RenderScript wallpaper crashes remain a separate unresolved issue;
these disabled-driver corrections do not establish their cause or fix.

## Android 4.4 IPC, logger and memory

Retain the physically working Binder protocol 7, legacy logger v1/v2, ashmem
and donor VM implementations. This stage changes no Binder, ashmem, logger,
LMK or core memory-management driver and no reserved-memory layout.

The native pre-init ABI probe now additionally tests only its own private 4 KiB
ashmem region: returned name, initial pin status, rejected out-of-range pin,
unpin/repin status, permissible reclaim, preserved or zero-filled contents as
appropriate, reduced protection, rejected protection escalation and denied new
writable mapping. No global purge, allocation stress or Binder transactions
are introduced. Existing block protection checks retain NULL control payloads
and never write to a block descriptor.

The actual probe passes success, permitted-purge and injected failure scenarios
for both supported release identities; bootstrap/image regressions also pass.
Its new static ARM binary has no dynamic loader/dependencies or NEON requirement.
**The expanded probe has not run on hardware.** Image 33's tested binary is
preserved; no existing boot artifact was overwritten.

## Next implementation and physical gates

1. Keep image 33 as the software-graphics/touch control. Package the expanded
   ABI probe separately and validate it before attributing memory failures.
2. Identify installed DRAM and process/speedo facts through supported read-only
   interfaces. Reconcile Motorola constraints and rail relationships, then make
   regulator failures veto unsafe frequency increases. Do not import Samsung
   EMC, regulator, display, pinmux or power tables.
3. Complete cpufreq bus/CPU ordering and rollback tests with regulator failures;
   only then prepare a stock-capped fixed-rate hardware experiment.
4. Prepare a separate legacy memory/host profile with one owner for GART,
   host and display resources. Validate bounded nvmap object lifetime/cache
   behavior before command submissions; exercise the explicit Motorola header
   mode before GPU rendering. Keep the current DRM software control intact.
5. Build a matched Motorola EGL/gralloc/HWC dependency set, resolve fence
   ownership and asynchronous ordering, then test actual composition. Use the
   existing Wingray wrappers rather than substitute Samsung-specific controls.

Kernel source is clean at `72368936`; device source is clean at `53dfbe3`.
All hardware results remain those explicitly documented for the tested images.
