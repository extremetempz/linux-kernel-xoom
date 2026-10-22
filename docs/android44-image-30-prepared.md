# Image 30: installed Android startup experiment

Prepared offline on 22 October 2026, then tested separately. **Image 30 reached
Android init and SystemServer, but aborted in EventHub before boot completion.**
See the [physical result](trace-boot-attempt-30.md). A lockscreen, touch and full
framework compatibility remain unverified. The original boot/recovery backups
remain unchanged; the image builder itself performs no device operation.

## Purpose and implementation

The next useful gate is the real installed Android startup process. This image
uses the installed Android 4.4 ROM with the separate legacy Binder protocol-7
kernel profile. Future Android 8.1 work retains its distinct ABI requirement.

- The bootstrap remains PID 1 through both `exec` transitions into the original
  Android init. `/sbin/ueventd` and watchdogd point to `/init.android`; ueventd
  keeps its own invocation name and original permissions/coldboot sequence.
- `androidboot.hardware=stingray` and normal boot mode are supplied before init
  establishes read-only properties. The original BOOTCLASSPATH is retained.
- Init imports are restricted to environment and generated RAM-data board setup.
  Legacy USB/modem services, EOS imports, recovery updater and critical-service
  recovery reboots are omitted. Per-service RAM log directories use the service
  UID because init drops privileges before launching the wrapper. The wrapper
  preserves inherited environment and property/socket descriptors.
- The profile marks eMMC read-only before disk exposure, rejects raw MMC ioctls
  and rejects `BLKROSET`. The latter is separate donor commit `400dbc8e`, patch
  0055: the generic block layer otherwise accepts the driver's `-EINVAL` and
  changes its reported RO flag. The driver's `md->read_only` still blocked write
  opens before this correction; a data-write bypass has not been demonstrated.
- A static ARM, non-NEON ABI probe first requires rejected write opens on the
  whole device and all ten partitions. It never writes those descriptors. Raw
  MMC and `BLKROSET` tests use NULL payloads, which cannot request a hardware
  command or clearing the flag even if the protection is missing. It also checks
  Binder version, private ashmem, logger v1/v2 round-trips and core sockets.
- The bootstrap requires exact capacity, all ten verified BigPart extents and
  eleven RO flags. It mounts only p8 as ext4 `ro,noload,nosuid,nodev`; `/data`
  and `/cache` are fresh tmpfs. Existing userdata/cache/recovery are not mounted.
  Thirteen previously captured fixed system references are SHA-256 checked;
  this is not a hash or integrity check of the entire installed system.
- The tested fixed framebuffer mode is reapplied. Approved default HALs and the
  installed software GLES library are copied to RAM. The exact software driver
  name `libGLES.so` is provided, while legacy NVIDIA HALs are hidden by read-only
  RAM binds. Bind-remounts use explicit source/target and retain nosuid/nodev.
- A background fixed PING/REPORT USB server remains available. Android reports
  add bounded stages, ABI results, mounts, service logs, selected properties,
  logcat, memory, power requests and RAM-only tombstones. There is no interactive
  USB shell. Native report commands have a fixed two-second kill timeout.

These are software protections for this experiment, not physical eMMC write
protection or isolation against arbitrary privileged kernel code. No real
write/clear-protection test has been attempted.

## Offline checks and evidence

The final artifact location, hash and audit are recorded in ignored
`artifacts/android44-image-30-ready/manifest.json` and `boot-image-audit.json`.
The prepared image is 3,481,600 bytes; SHA-256:
`a5b16f0ca7ac80a3d232e8ca4f5fc059fcc9fbac0a71c16d5a3d10d8c274c93d`.
The preliminary image-30 directories preserve earlier assembled revisions;
they are superseded by `android44-image-30-ready`.

Checks include:

- Real kernel compilation and configuration/DT/symbol verifier, with the
  tested USB/display/BigPart topology retained.
- Static ARM native helper builds, target ioctl size/protocol assertions,
  source/binary hash matching, and no dynamic dependencies or NEON attributes.
- Actual ABI-probe control flow against mocked syscalls: success and 54 failures,
  including unexpected write-open admissions and rejected NULL control ioctls.
- Actual kernel MMC and generic `blkdev_roset` dispatch under UBSan across 384
  scope/privilege/payload combinations, plus the existing 64 scope cases.
- Actual logger write-path fault/wrap/concurrency checks; existing framebuffer
  bounds/drawing and pin capability regressions.
- Eight archive/startup/header tests, six actual-bootstrap success/failure tests,
  eighteen framing/storage-policy tests and seven actual Android report tests.
- Boot v0 addresses, gzip decompression destination, appended DTB alignment,
  component checksums and image size below the preserved 8 MiB boot partition.
  Archive transforms are in memory; original files are not extracted over or
  modified. Existing output directories and stale native manifests are refused.

Host tests mock kernel interfaces/mounts where indicated. They do not establish
physical Android ABI behavior, real mount success or framework compatibility.

## Reproduction

Use fresh output directories. The local original boot backup, pinned BusyBox and
previously captured fixed ROM references under `artifacts/lockscreen-reference-28`
are prerequisites. They intentionally remain private/ignored. Preparation does
not retrieve anything from a connected tablet and never invokes a flashing tool.

```bash
XOOM_PROFILE=android44 XOOM_BUILD_ROOT=/tmp/xoom-android44-build XOOM_ARTIFACT_DIR="$PWD/artifacts/android44-local" bash scripts/build-wingray.sh
XOOM_BUILD_ROOT=/tmp/xoom-android44-build XOOM_ARTIFACT_DIR="$PWD/artifacts/android44-local" bash scripts/build-android44-probe.sh
XOOM_BUILD_ROOT=/tmp/xoom-android44-build XOOM_ARTIFACT_DIR="$PWD/artifacts/android44-local" bash scripts/build-display-pattern.sh
python3 scripts/prepare-android44.py --kernel-dir artifacts/android44-local --runtime-dir artifacts/android44-local --output-dir artifacts/android44-image-local
python3 scripts/audit-boot-image.py --candidate artifacts/android44-image-local/wingray-android44-ramdata.img
```

## Remaining uncertainties and next hardware gate

The user subsequently requested a boot-only hardware test after offline checks.
Retain the original restoration cycle; no physical result is recorded in this
preparation document. First collect a fresh report with explicit
`--storage-mode android44-readonly`. Ordinary diagnostic mode still rejects
Android mounts. Reports are saved and checksummed before mount-policy rejection,
so a failed startup or non-atomic mount snapshot remains inspectable.

Check the ABI and bootstrap stage first, then original init/service stability,
zygote/SystemServer, SurfaceFlinger and the visible screen. Framework completion
or an unchanged RGB pattern alone does not prove the lockscreen.

The software graphics path is supported by tagged AOSP source: exact
`libGLES.so` lookup in [Loader.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-4.4.4_r2/opengl/libs/EGL/Loader.cpp),
ES1 fallback in [SurfaceFlinger.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-4.4.4_r2/services/surfaceflinger/SurfaceFlinger.cpp),
and the qemu-property presence gate in [GLES20Canvas JNI](https://android.googlesource.com/platform/frameworks/base/+/android-4.4.4_r2/core/jni/android_view_GLES20Canvas.cpp).
Using `ro.kernel.qemu=0` with `ro.kernel.qemu.gles=0` is an inference from these
paths, not proof that the custom installed EOS framework behaves identically.
Some installed libraries advertise NEON attributes despite the working Tegra 2
ROM; newly exercised paths may still fault. Native tombstones/logs are needed.

Fresh RAM data is unprovisioned. Tagged [KeyguardViewMediator](https://android.googlesource.com/platform/frameworks/base/+/android-4.4.4_r2/packages/Keyguard/src/com/android/keyguard/KeyguardViewMediator.java)
can suppress keyguard before provisioning. The first Android UI may therefore
be setup wizard or launcher. After proving framework startup, a later fixed
RAM-only step can set and verify `device_provisioned`/`user_setup_complete`;
automatic provisioning or zygote restarts are deliberately not in this image.

The missing legacy alarm device has explicit handler/monotonic fallbacks in
tagged [AlarmManagerService](https://android.googlesource.com/platform/frameworks/base/+/android-4.4.4_r2/services/java/com/android/server/AlarmManagerService.java)
and [SystemClock](https://android.googlesource.com/platform/system/core/+/android-4.4.4_r2/libutils/SystemClock.cpp).
It is not a demonstrated first-lockscreen blocker. Suspend/wake alarms, input,
GPU acceleration and other peripherals remain unvalidated. Fresh DEX/data
generation may exceed the current RAM budget; this must be measured on target.
