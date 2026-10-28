# Retained-console integrity candidate 84

28 October 2026. Based on main `14223f6` (merged PR #23), following
PR #22 and the IRQ/backlight validation in PR #21. **Built and checked
offline only. No flash, reset, suspend, live device access or partition write.**

## What the latest PR establishes

PR #23 correctly fixes this donor's nonstandard ramoops size binding:
`record-size`, `console-size` and `pmsg-size` need u64 values. Its hardware
results prove the corrected memory-region binding, read-only mount and intended
1 MiB layout. Those changes are retained. The earlier candidate-83 checks
missed the driver's u64 size requirement; a correct reservation alone was not
enough to establish a successful probe.

The saved `trace83fix-before` and `trace83fix-after` wire frames both pass
their original nonce, decoded length and SHA-256 checks and match the saved
payloads. The earlier boot marker contains `5a938e4d-...`; its retained copy
contains `5a9s8e4d-...`. ASCII `3` (0x33) to `s` (0x73) differs by bit 6.
The later normal report has the same current boot UUID as the after capture,
so it is not another reset sample.

This verifies that the discrepancy already exists in the device's captured
report, rather than being introduced by the saved serial transfer. It does
**not** prove a faulty DRAM cell, reset controller, cache mapping, writer race
or particular bootloader overwrite. The reset cause and corruption location
remain unknown. The old log reported `ecc: 0/0`: it had no error correction.
No old failure log can be recovered retroactively by this change.

PR #23's normal-report fix accepts the three fixed radio/module RAM overlays
and read-only pstore. That compatibility is preserved and regression-tested.
The host validator now additionally checks pstore's read-only state in both
mount snapshots and rejects stacked pstore mounts, avoiding a false read-only
verdict when snapshots disagree.

## Focused correction using existing donor code

Patch **0156** adds `wingray_android44_wakeirqecc_defconfig` and
`tegra20-motorola-wingray-android44-wakeirqecc.dts`. It includes the corrected
trace83 DT and adds only a diagnostic marker and **u32** `ecc-size = <16>`.
The donor reads ECC size as u32, unlike the three u64 log sizes.

This enables the existing `fs/pstore/ram_core.c` Reed–Solomon implementation:
16 parity bytes per 128-byte data block, with separate header protection.
It can correct up to eight erroneous byte symbols per block. Errors beyond
that capacity are not guaranteed to be detected or corrected; the independent
known-payload comparison is still required. No new ECC driver is introduced.

The reservation union, 1 MiB ramoops base/extent and three crash/console/pmsg
zone sizes are unchanged. Parity consumes space **inside** those zones, so
usable log capacity decreases. This is a new persistent-log format: **ECC
and no-ECC images are not interchangeable recovery readers**. Existing IRQ,
CPCAP transport, display timings, clocks, panel power, regulators and charging
settings are unchanged. The new config differs from trace83 only in the
selected appended DT. PM, SUSPEND, DC resume and DVFS remain disabled.

The new DT marker also enables one harmless boot-time kernel-console probe:
a boot UUID, 256-character fixed pattern and SHA-256 digest. The exact line
is saved in RAM at `/run/pstore-probe.txt` and included in the fixed PSTORE
report. It spans at least three 128-byte ECC blocks. Existing profiles do
not emit this additional probe. The report shows the DT ECC property;
`/sys/module/ramoops/parameters/ecc` is deliberately not used as evidence
because this donor does not update that module parameter after a DT probe.

## Offline checks completed

- Full ARM kernel, modules, built-in runtime and boot-image build/pack pass.
  The runtime archive matches the linked built-in archive, and all recorded
  source hashes and image hashes match.
- Compiled DT/config checks preserve the reservation union and board wiring,
  enforce the exact ECC scope and reject wrong ECC widths, missing markers,
  changed DC wiring and reservation changes. The previous corrected no-ECC
  trace83 artifacts still pass their original checks.
- `test-pstore-ecc.py` compiles the donor's actual RS encoder/decoder and
  persistent-RAM functions. A synthetic reset reproduces `3` → `s` without
  ECC, restores it with ECC, restores eight corrupted symbols, damaged ring
  headers and parity, and reports an injected uncorrectable block. Only host
  allocation/IO-copy/locking primitives are mocked. It does not test ARM
  memory attributes, real reset retention or electrical hardware behaviour.
- The actual boot-probe shell block is executed against temporary files:
  disabled outside the marker, exact payload/hash inside it. The actual
  read-only report handles a full configured set of retained records,
  reports truncation and preserves fixture files.
- The offline retention checker revalidates original wire frames and saved
  payload/status hashes. It rejects the historical corrupted marker, stale
  same-boot samples, current dmesg masquerading as the previous console,
  wrong layout, partial capture, missing ECC status, unrecoverable errors
  and altered known probes. Corrected-byte counts remain visible.
- Existing CPCAP ON handler/transport, LP8550/fb callbacks, battery,
  Bluetooth, compiled display scope and framed-report regressions pass.

## Build and image identity

Apply the exported series through **0156** to the pinned donor before building.
Use fresh output directories; the existing tested images must stay untouched:

```sh
XOOM_ANDROID_GPU_PROFILE=wakeirqecc \
XOOM_BUILD_ROOT=/tmp/xoom-retention84-fresh \
XOOM_ARTIFACT_DIR="$PWD/artifacts/retention84-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/retention84-new-ready" \
bash scripts/build-android-gpu.sh
```

Prepared locally:

- `artifacts/retention84-ready/wingray-android44-gpu.img`
- 4,151,296 bytes
- SHA-256 `eaa6486d9bf887e3b2bdb49215c3d58b289417bdecdc90254138150fa9104e7e`
- Kernel source commit `b3393c36`; new patch reproduces its two new files.
- Manifest: `retained_console_ecc_test=true`, hardware validation false,
  `dc_resume_experimental=false`, `soc_suspend_enabled=false`.

Private ROM inputs, raw reports and this experimental image are not published.
The reproducible code, patch, tests and procedure are committed.

## Manual hardware gate — not executed by this work

1. Preserve the complete original boot/recovery backups and hashes, working
   IRQ/backlight image and a verified physical-button fastboot recovery path.
   Use only a separately authorised boot-partition test; no recovery or layout
   changes. Do not trigger a deliberate panic.
2. Boot the new ECC image. Treat any old record from the **first** ECC boot
   as incompatible residue; do not score it. Capture a fresh PSTORE report
   with the existing fixed requester into a new private directory, for example
   `artifacts/retention84-before`. Confirm backend binding, mount success,
   expected sizes, `RAMOOPS_DT_ECC_HEX 00000010` and the current probe.
3. Perform a normal, operator-controlled warm reset into the **same image**.
   Do not restore the original ROM between these captures: it uses a different
   legacy console format and may overwrite this RAM. Save the new PSTORE
   capture as `artifacts/retention84-after1`. Do not delete pstore records.
4. Run the offline check:

   ```sh
   python3 scripts/check-pstore-retention.py \
     --before artifacts/retention84-before \
     --after artifacts/retention84-after1
   ```

   Require `gate_passed: true`, different boot UUIDs, an exact previous marker
   and probe inside **old `console-ramoops-0`**, and zero unrecoverable blocks.
   Corrected bytes may be nonzero and must be recorded; correction is not
   evidence that the underlying corruption source has been resolved.
5. Repeat another warm reset into the same image. Capture `after2` and compare
   `after1` → `after2`. Require both consecutive comparisons to pass. A second
   capture without a reset must fail. Any missing record, damaged probe or
   unrecoverable block stops progression; retain all original files privately.
6. Only after that evidence should a **separate** DC-instrumented candidate
   be prepared. Reproducing the existing combined IRQ/DC failure still needs
   checkpoints around DC disable/enable/flip locking with matched ECC recovery.
   Do not enable suspend or rerun the known failing DC image as part of this
   retention test. An operator-approved recovery from a hard hang later also
   needs validation; normal warm reset success does not establish it.

The checker is entirely offline and issues no serial, ADB, flash, reboot,
sysrq, suspend or power-control operation. One pass verifies the known probe
across one reset, **not every byte of every retained record**, physical wake,
DC recovery, actual low-power entry or power savings. Suspend remains gated.

## Rollback

No automatic action is supplied. For a later authorised hardware test, use the
established physical-button fastboot procedure and restore the preserved
working boot image only. Leave recovery and partitions untouched. After the
original ROM starts, verify the complete boot/recovery hashes using the
existing readback procedure. Archive the ECC captures before changing formats.
