# Retained-console candidate 83 — establish evidence before DC/suspend tests

27 October 2026. Reviewed main `c757f1f`, PRs #20/#21 and commits
`4078a21`, `76d5f4f`, `211267f`, `ab81178`. **Nothing was flashed, rebooted
or suspended during this work.** No live device or partition access occurred.

## Revised accepted state

ON IRQ-only delivery, Tegra LIC routing/dynamic virq, polling removal and
IRQ + backlight-only display cycles are hardware-validated. The report
records 26 ON events, zero errors and no unmasked-pending bit or parent IRQ
disable. These prerequisites do not need to be reimplemented.

Candidate 81 worked in its standalone test. The combined full-wakeirq/DC
profile later lost display wake and USB. The successful backlight-only
isolation points toward the DC transition, but there is still no recovered
failure log proving a specific deadlock, clock, register or panel fault.
This happened with PM/SUSPEND off, so it was **not a deep-sleep failure**.

Use the proven IRQ/backlight-only combination as the current baseline, not
the combined DC profile. Test 5 remains the conservative rollback. Suspend,
DVFS, regulator changes and charger controls stay disabled.

## Three verified log-capture gaps corrected

1. **Ramoops binding:** the donor's `fs/pstore/ram.c:ramoops_parse_dt()`
   explicitly requires a `memory-region` phandle. Wingray had only a consumer
   `reg`, hence the observed `no memory-region phandle` and failed probe.
   Patch 0154 supplies that phandle in a new opt-in DT.
2. **Mount:** the RAM runtime filters original Android pstore mount commands,
   and its bootstrap did not mount pstore. Only the new DT marker enables
   a read-only `ro,nosuid,nodev,noexec` mount. Failure is recorded in RAM and
   does not prevent USB diagnostics from starting. Backend binding and VFS
   mounting are reported separately; an empty directory proves neither.
3. **Transfer capacity:** the configured console alone is 512 KiB, and the
   three 128 KiB crash slots plus 128 KiB pmsg fill the remaining space. The
   old 512 KiB payload / 600,000-byte wire limit could reject a valid full
   capture. PSTORE now permits a bounded 2 MiB payload / 3 MiB base64 wire.
   Normal REPORT limits are unchanged. The read-only script has a 1.5 MiB
   aggregate file budget, explicit truncation notices, bounded last_kmsg and
   dmesg tails, and never deletes records. Duplicate console capture is gone.

The report identifies the current boot UUID, backend binding, mount status
and actual ramoops parameters. A harmless `XOOM_PSTORE_BOOT <uuid>` kernel
console marker is emitted only by the trace-profile bootstrap. It permits
an ordinary warm-reset retention check without deliberately causing a panic.

## Reserved memory ownership

The existing reserved union is unchanged: `[0x1fe00000,0x20000000)` (2 MiB).
The new profile splits it into adjacent, non-overlapping reservations:

| Region | Purpose |
|---|---|
| `0x1fe00000`–`0x1fefffff` | Existing SMP/startup trace; retained first MiB |
| `0x1ff00000`–`0x1fffffff` | Ramoops memory-region, no-map, retained second MiB |

Do not add a new 1 MiB reservation on top of the old 2 MiB reservation: that
would create overlapping owners. The new DT shrinks the legacy-console node
before adding the ramoops child. All framebuffer/carveout, warmboot and other
reservations, rails, pinmux, SPI/IRQ cells, GPU/touch/radio/battery properties
remain unchanged. The compiled validator checks the exact reservation union,
non-overlap, phandle, sizes and all unrelated DT properties.

Layout within the ramoops MiB remains three `0x20000` dmesg records, a
`0x80000` console and `0x20000` pmsg. Existing profiles and images are not
modified. No generic ramoops driver change or speculative physical address
is introduced.

Patch 0153 also exports the already hardware-tested wakeirqbl defconfig from
the ignored donor. PR #21 added its build selector but did not export that
source change; a fresh source checkout otherwise cannot reproduce it.

## Build and offline checks

Apply the numbered kernel patch series through 0154 to a fresh pinned donor
before building. Do not reapply it blindly over a patched working donor.

```sh
python3 scripts/fetch-sources.py
python3 scripts/apply-kernel-patches.py
XOOM_ANDROID_GPU_PROFILE=wakeirqtrace \
XOOM_BUILD_ROOT=/tmp/xoom-trace83-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/trace83-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/trace83-new-ready" \
bash scripts/build-android-gpu.sh
```

Prepared: `artifacts/trace83-ready/wingray-android44-gpu.img`, 4,147,200 bytes.
SHA256: `6e8d2b08739c4b86c3249762fc1ada0cf2cd70835b573869ded878c85ae8029b`.
Full ARM kernel/DT/module build and matched built-in runtime/image checks
pass. Manifest: `android44-wakeirqtrace`, retained-console hardware validation
false, DC-resume experiment false and SoC suspend false.

Passed offline checks include compiled memory-layout/phandle tests with
missing/wrong handles, overlap, size, no-map and partition negative controls;
actual report execution against a complete configured set of pstore fixture
files; unchanged contents after capture; large/fragmented frames through 2 MiB;
bad nonce/hash/encoding/size controls; existing ON IRQ/transport, LP8550,
battery, Bluetooth and display scope checks.

**Hardware retention remains unverified.** The driver binding, a successful
build or one empty first-boot pstore directory is not proof that logs survive
the bootloader and the tablet's physical reset sequence.

## Next hardware gate — warm reset, no failure injection

Only after separate authorization, preserve the original boot/recovery and
the existing tested images, hashes and physical fastboot restoration path.

1. Boot the new backlight-only trace image. Capture normal diagnostics and
   a fixed PSTORE snapshot with `scripts/run-pstore-report.py` using a new
   private artifact directory (use `--timeout 60` if needed).
2. Require a bound ramoops device, successful read-only mount and parameters
   matching the layout above. Record current boot UUID A and its boot marker.
   Old console files may legitimately be absent on the first valid boot.
3. Perform one operator-controlled **warm reset into the same corrected
   image**, without disconnecting battery/power or booting another ROM.
4. Capture PSTORE immediately after boot B. The current UUID must differ,
   and an old `console-ramoops-*` record must contain boot A's exact marker.
   Save the raw framed result, checksum and backend/mount status privately.
5. If that fails, stop: retention is still unavailable. Do not enable DC
   shutdown or suspend and do not substitute current dmesg for the lost log.

No panic, sysrq crash, suspend write or reset command runs automatically.
Pstore is RAM-backed: power loss, bootloader writes and subsequent boots may
destroy evidence. A hard stop can prevent the final log message from being
written. Absence of a message is not proof that a particular function ran.

## Recovery requirements for a later failing DC test

Only after the warm-reset gate passes should a separately instrumented DC
test be prepared. Its safe recovery image must use **the same corrected
reserved layout, ramoops binding and record sizes**. Boot that trace-capable
backlight-only recovery directly and collect the previous log before another
reset. Test 5 has the old broken binding; the original 2.6.39 ROM uses a
different ramconsole format at this address. Neither is a substitute for
matched pstore recovery, and booting the old ROM can overwrite the evidence.

The earlier full-wakeirq failure cannot be retroactively recovered by this
fix. Reproduce it only after retained evidence has been proved and kernel
owner checkpoints around DC/clock/window/lock operations have been reviewed.

## Revised suspend sequence

1. Keep the validated IRQ/backlight baseline.
2. Prove retained logging with warm resets.
3. Reproduce and diagnose the combined DC failure with matched recovery.
4. Revalidate combined IRQ/DC cycles and peripherals.
5. Then prepare a separate PM/GPU/device-callback framework profile, real
   wake arming and CPU1 hotplug tests. Existing GPU guards still exclude
   CONFIG_SUSPEND; do not simply delete that guard.
6. Test conservative CPU-complex LP2 first, then consider LP1's memory
   self-refresh/IRAM requirements. LP0 and Android automatic suspend remain
   excluded until their respective wake/device/retention gates pass.

No new power-saving or low-power wake claim follows from this delivery.
