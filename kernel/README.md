# Linux 4.4.147 Wingray bring-up

**Latest physical test:** bootloader 1050 rejects RAM boot. With user approval,
a diagnostic image was written to boot; it remained at the Motorola logo and
produced no USB serial device. The new kernel is not boot validated. See
[the test record](../docs/hardware-validation.md) for restoration status and
evidence. The original boot partition has been restored and verified byte for
byte, and the working Android ROM is running. The sections below preserve the
earlier compiled milestones.

## Chosen fork

- Upstream: [Decatf/linux, android-4.4-p4wifi](https://github.com/Decatf/linux/tree/android-4.4-p4wifi).
- Base commit: `bbcece6d21c83b6280061a91d27566aff1951c94`.
- Local development branch: `codex/wingray-4.4`.
- Modified source commit: `5bf34d336ae657c03cac8609f073c46698c774a3`.
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

The checked build is preserved in `wingray-bringup-artifacts.tar.gz`, with provenance in `build-report.json` and compiler output in `build-output.txt`. The archive is for inspection and subsequent bring-up preparation, not flashing. It contains no ROM or ramdisk.

## Validation and remaining work

The source cross-compiles to an ARM zImage and appended Wingray DTB. Native tests exercise the actual BigPart implementation with sanitizers, including 1,000 userdata capacities. An alternate Git index test confirmed that the patch reconstructs the modified source tree exactly. Artifact verification checks the ARM image magic, appended DTB bytes, board identity, memory node, eMMC/controller opt-in, USB peripheral selection, and important configuration gates.

**Not yet a finished kernel port.** No hardware boot, eMMC read test, USB enumeration or GPIO key test has occurred. Screen, touch, Wi-Fi, audio, Bluetooth, cameras, battery/charging control and suspend are not implemented or validated. CPU frequency scaling, CPU idle and suspend are disabled, and the kernel relies on firmware-initialized power rails. The video engines remain disabled and legacy reserved memory is intentionally retained.

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

These additions do not prove working display, touch or Wi-Fi. No new-kernel
boot has been attempted. Suspend, DVFS, charging, fuel gauge, audio, Bluetooth,
cameras and sensors remain pending. Keep the existing ROM and recovery.
