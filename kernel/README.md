# Linux 4.4.147 Wingray bring-up

**Early-boot review:** [findings and staged plan](../docs/early-boot-review.md).
The existing 0x8000 decompression fix was verified in the failed binary.
No root cause or new hardware fix is established. A separate UP/no-peripheral
profile compiles; it has not been boot tested. Original images are preserved.

**Latest physical test:** candidate 11 remained at the Motorola logo, then
re-enumerated as fastboot after about three minutes. Its valid trace ended at
the same sampled PFN (`0x2ebff`) as candidate 10 inside `memmap_init_zone`;
return and fatal-PC markers were absent. This repeats the sparse-profile
checkpoint, not an exact fault address or proof of a permanent hang. The
original boot and recovery images were read back byte-for-byte after
restoration, and Android returned. See the [candidate 11 record](../docs/trace-boot-attempt-11.md).

Candidate 12 is built with active-zone bounds and a narrow page-progress
window around PFN `0x2ebff`. It has passed offline checks but has not been
physically tested; see the [candidate 12 plan](../docs/trace-boot-attempt-12-prepared.md).

The bootloader 1050 also rejects RAM boot with error 0x8, so diagnostic tests
use the boot partition only. The original Android ROM is running after the
latest restoration.

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

**Not yet a finished kernel port.** Boot-only diagnostic images have been tested and the verified original restored. Linux 4.4 reached sampled progress inside `memmap_init_zone` but did not reach Android or produce diagnostic USB serial. No new-kernel eMMC read or GPIO key test has been performed. Display, touch, Wi-Fi, audio, Bluetooth, cameras, charging and suspend remain unvalidated on this kernel. CPU frequency scaling, CPU idle and suspend are disabled, and the kernel relies on firmware-initialized power rails. The video engines remain disabled and legacy reserved memory is intentionally retained.

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
