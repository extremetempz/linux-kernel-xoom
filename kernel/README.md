# Linux 4.4.147 Wingray bring-up

**Early-boot review:** [findings and staged plan](../docs/early-boot-review.md).
The existing 0x8000 decompression fix was verified in the failed binary.
Later tests identified and corrected a lowmem-zone sizing defect and a
diagnostic hook calling freed init code. Original images are preserved.

**Latest display test:** image 29 shows an operator-confirmed RGB pattern under
Linux 4.4. Two fresh reports verify 1280×800×32 fb0, connected/enabled LVDS,
capped P3 backlight control, DC interrupt progression and retained USB/storage.
The LCD pull-capability correction and exact backlight rejection logs are
separate source commits. Original boot/recovery are fully verified after
restoration. See [image 28 failure](../docs/trace-boot-attempt-28.md) and
[image 29 success](../docs/trace-boot-attempt-29.md).

**Storage milestone:** image 26 boots Linux 4.4 diagnostic userspace,
enumerates USB and passes two fresh checksum-verified storage reports. Full
eMMC capacity (62,521,344 sectors) and all ten BigPart partition extents match
the working kernel. The scoped capacity correction and exact GPT boot-option
parser are separate source commits/patches. See [image 24](../docs/trace-boot-attempt-24.md),
[image 25](../docs/trace-boot-attempt-25.md) and [image 26](../docs/trace-boot-attempt-26.md)
for the evidence, intervening regression and correction.

Original boot was restored and full boot/recovery readbacks match; Android is
running on its original kernel. No Android filesystem mount or on-disk GPT
change occurred in these diagnostics. Touch, Wi-Fi, power management and Android startup under Linux4.4 remain unverified. The active objective is the real Android lockscreen, with ABI/init/graphics integration next and unrelated peripherals deferred.

The bootloader 1050 also rejects RAM boot with error 0x8, so diagnostic tests
use the boot partition only. The original Android ROM is running after the
latest restoration.

## Chosen fork

- Upstream: [Decatf/linux, android-4.4-p4wifi](https://github.com/Decatf/linux/tree/android-4.4-p4wifi).
- Base commit: `bbcece6d21c83b6280061a91d27566aff1951c94`.
- Local development branch: `codex/wingray-4.4`.
- Initial port source commit: `5bf34d336ae657c03cac8609f073c46698c774a3`.
- Latest hardware-tested diagnostic source: `a8a26819` (image 29), reconstructed by patches 0001–0050.
- The patch in `patches/0001-wingray-bringup.patch` reconstructs that exact source tree from the base. It includes new files, not just changes to existing files.

The private GitHub repository stores this patch series and the build workflow. Fetching the pinned base and applying the patch reconstructs the complete modified kernel source under `sources/kernel-donor`. This is not a separate GitHub fork containing every upstream kernel file.

## Implemented

- Dedicated MZ604 device tree and non-NEON ARMv7 config, with appended DTB and legacy ATAG command-line compatibility.
- 1 GiB RAM description, preservation of legacy video/console memory, and early reservation of firmware framebuffer/LP0 regions supplied in boot arguments.
- Eight-bit eMMC on SDMMC4, at a conservative maximum 25 MHz.
- UARTB debug, GPIO volume keys, and Xoom USB data switch/force-on wiring.
- Peripheral USB controller/PHY timing from the Xoom board sources, USB ACM serial gadget, and ramoops logging.
- Xoom-only BigPart GPT view with controller opt-in, legacy-triplet validation, bounds/overlap checks and no GPT writes.
- Samsung-only GPIO tables, board objects and machine initialization are excluded from Wingray; downstream nvhost hooks are gated so a minimal kernel can link without the Samsung graphics stack.
- DTC lexer fix for modern host compilers; pinned official Android GCC 4.9 toolchain, with its Python wrapper adjusted for Python 3.

## Build

From the repository root:

```sh
python3 scripts/fetch-sources.py
python3 scripts/apply-kernel-patches.py
bash scripts/setup-toolchain.sh
bash scripts/test-bigpart.sh
bash scripts/build-wingray.sh
```

Host requirements: Linux x86-64, Python 3, Git, curl, rsync, make, host GCC/binutils, bison, flex, bc, tar, gzip and SHA-256 utilities. Build paths are mirrored into `/tmp` because these old kernel makefiles reject spaces. `XOOM_BUILD_ROOT` may specify a dedicated build directory without spaces; `JOBS` controls concurrency. Temporary build directories are retained for debugging.

Outputs go to `artifacts/wingray44/`: `zImage`, `zImage-dtb`, DTB, resolved config, System.map and SHA256SUMS. These files are **not** an Android boot image. A matching ramdisk, measured boot image layout and a recovery/rollback plan are needed before a hardware boot test.

For the current minimal RAM diagnostic, using the preserved original boot
header already captured in this workspace:

```sh
python3 scripts/fetch-diagnostic-runtime.py
XOOM_PROFILE=diagnostic bash scripts/build-wingray.sh
python3 scripts/prepare-diagnostic.py --kernel-dir artifacts/wingray-diagnostic --output-dir artifacts/new-static-diagnostic
```

Choose a new output directory for each prepared image; existing evidence is
never overwritten. The builder defaults to the pinned static ARM BusyBox.
`--android-runtime` explicitly reproduces the earlier copied Android runtime
for investigation; that runtime requires property-workspace context absent
from the standalone diagnostic. These commands do not access or flash a device.

The checked build is preserved in `wingray-bringup-artifacts.tar.gz`, with provenance in `build-report.json` and compiler output in `build-output.txt`. The archive is for inspection and subsequent bring-up preparation, not flashing. It contains no ROM or ramdisk.

## Validation and remaining work

The source cross-compiles to an ARM zImage and appended Wingray DTB. Native tests exercise the actual BigPart implementation with sanitizers, including 1,000 userdata capacities. An alternate Git index test confirmed that the patch reconstructs the modified source tree exactly. Artifact verification checks the ARM image magic, appended DTB bytes, board identity, memory node, eMMC/controller opt-in, USB peripheral selection, and important configuration gates.

**Not yet a finished kernel port.** Boot-only diagnostic images have been tested and the verified original restored. Linux 4.4 now reaches diagnostic userspace mount activity, with no fatal event recorded by candidate 20, but has not reached Android or produced diagnostic USB serial. Continuous userspace activity and complete script execution remain unverified. No new-kernel eMMC read or GPIO key test has been performed. Display, touch, Wi-Fi, audio, Bluetooth, cameras, charging and suspend remain unvalidated on this kernel. CPU frequency scaling, CPU idle and suspend are disabled, and the kernel relies on firmware-initialized power rails. The video engines remain disabled and legacy reserved memory is intentionally retained.

Further development requires CPCAP/MAX8649 power support, Xoom pinmux and peripheral sequencing, then hardware boot logs and storage geometry validation. Do not flash this kernel over a working install or use it to start ROM integration yet. No flashing/repartitioning scripts are supplied.

## Peripheral bring-up update

Source commit `4242b8a1` is preserved by `patches/0002-wingray-peripherals.patch`.
The second patch adds the actual P3/AUO board pinmux, display/backlight,
maXTouch reset/wake/IRQ, BCM4329 SDIO sequencing, external SD, CPCAP MFD and
Wingray regulators, MAX8649 DT support and restart/power-off GPIOs. It also
handles the measured relocated GPT and fixes decompression for the existing
Android boot image load address. The first milestone's limitations above
describe its original build; current hardware evidence and remaining work
are maintained in [hardware-validation.md](../docs/hardware-validation.md).

These additions do not prove working display, touch or Wi-Fi. Diagnostic
Linux 4.4 boots have been attempted but have not reached Android. Suspend,
DVFS, charging, fuel gauge, audio, Bluetooth, cameras and sensors remain
pending. Keep the existing ROM and recovery.

### Isolated panel-supply/I2C readiness profile

```sh
XOOM_PROFILE=panelbus bash scripts/build-wingray.sh
```

Use `scripts/prepare-diagnostic.py --panelbus` only with this isolated kernel.
It includes guarded fixed LP8550 register reads and virtual metadata; the broad
peripheral profile remains unvalidated. This stage does not enable DRM, the
backlight driver, touch, PMIC/CPU-rail drivers, Wi-Fi or suspend.

## Tested display profile

`XOOM_PROFILE=display` selects `wingray_display_defconfig` and
`tegra20-motorola-wingray-display.dtb`. It retains the tested USB/BigPart/PB2
path, adds DC0 RGB with shared LCD pull groups and the guarded P3 LP8550 driver,
and leaves GPU/DC1/HDMI/input/PMIC/CPU frequency/suspend disabled.

```bash
XOOM_PROFILE=display XOOM_BUILD_ROOT=/tmp/xoom-display-build XOOM_ARTIFACT_DIR="$PWD/artifacts/display-local" bash scripts/build-wingray.sh
XOOM_BUILD_ROOT=/tmp/xoom-display-build XOOM_ARTIFACT_DIR="$PWD/artifacts/display-local" bash scripts/build-display-pattern.sh
python3 scripts/prepare-diagnostic.py --kernel-dir artifacts/display-local --output-dir artifacts/display-image-local --display
```

The opt-in RAM diagnostic starts fixed color bars once independently of USB.
No Android partition is mounted; register reports go through the bound driver.
Host tests cover actual backlight policy, framebuffer bounds/drawing and script
behavior; pin tests cross-check the actual Tegra20 driver and reject image28's
failed configuration. Successful scanout is distinct from a running framework.

## Experimental installed-Android profile

`XOOM_PROFILE=android44` selects the isolated installed-ROM ABI and its own DTB.
Patches 0051–0054 add Binder protocol 7, ashmem, KitKat logger and a scoped
software read-only eMMC policy. Patch 0055 rejects `BLKROSET` in the same profile
before the generic block layer can change its RO flags. Other profiles retain
their existing behavior. These are volatile software policies, not hardware
write-protect programming or a security boundary against privileged kernel code.

The first Android experiment uses the validated display/storage topology and
RAM-backed data/cache; legacy NVIDIA HALs and GPU interfaces are bypassed using
RAM-only default/software graphics overlays. Image 31 has completed a physical Android 4.4.4 boot to Welcome; touch
remains disabled and lockscreen completion is unverified. See [image 30](../docs/android44-image-30-prepared.md) for offline
build steps, failure gates, evidence and remaining uncertainties.
