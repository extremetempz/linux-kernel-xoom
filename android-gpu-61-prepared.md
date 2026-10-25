# Image 61 prepared: display clock and P3 backlight initialization

25 October 2026. Prepared from Image 60 after the raw reports established two
independent display faults. This image is **not hardware tested**. Do not
describe its display as working until the boot-only test below has produced
fresh evidence.

## Patches

| Patch | Donor commit | Change |
|---|---|---|
| 0112 | `c24df0e9` | Apply OF assigned-clock defaults on the nvhost bus probe. The Wingray DC's `assigned-clock-rates = <598000000>` was compiled into the DTB but never applied, because nvhost is not a platform bus. PLL_C remained at the bootloader's 650 MHz, 66.4 MHz mode programming rounded to 65 MHz and was rejected, and the DC stayed disabled with zero interrupts. |
| 0113 | `8f748ef8` | Initialize the LP8550 P3 A1-A7 production registers before the existing readback verification. A cold boot left A1=0x60/A2=0x9f; the verify-only path returned -EINVAL and registered no backlight. The sequence is the Motorola vendor sequence and does not touch EEPROM control register 0x72. |

The patches are exported as `kernel/patches/0112-*` and `0113-*` and committed
separately on the `deepseek` branch.

## Image identity

- Path: `artifacts/androidgpu61-ready/wingray-android44-gpu.img`
- Size: 3,637,248 bytes
- SHA-256: `e9b626f22971aa4b2a7fdb0ea3dda377524b9d7f6ad7db2ff6823dd309c62949`
- Kernel: `4.4.147-wingray-android44-gpu`, cookie `0x584d0060`
- Appended DTB SHA-256: `e5ecf795f83616ca17ac2f5d5d6901349394ae85c475ff854cb384b6b7c82dbe`
- Kernel config SHA-256: `3f23f32b43c3f763c6cf817902377c39805865f5a4b06d8f6076aceb0590ab68`

The DTB and kernel config are byte-identical to Image 60. Only kernel code
changed. The image is under the preserved 8 MiB boot-partition size.

## Offline validation

- Full ARM `zImage-dtb` link passed; no errors and no new warnings. The only
  display warning is the pre-existing unused `tegra_dc_pclk_predict_rate`.
- `nvhost_drv_probe` disassembly contains a call to `of_clk_set_defaults`
  with `clk_supplier=false` and an error-return path before the driver probe.
- `lp855x_wingray_production` is present in the linked kernel; the program
  path is inlined into `lp855x_probe`.
- Updated `tests/test-wingray-backlight.py` passes: exact write order,
  A1-A7 values, per-write failure, per-read failure, stuck-register failure,
  no `0x72` write, unchanged brightness/A0 policy, 256 brightness values.
- `tests/test-wingray-panel-enable.py`, `tests/test-wingray-fb-bus-map.py`,
  `tests/test-gpu-fixed-emc.py` and `tests/test-tegra-dc-panel-guards.py`
  pass.
- Boot-header audit confirms the Android header, appended DTB, page sizes
  and addresses; the image SHA-256 matches the manifest.

## Expected hardware result

- No `can't divide 65000000` log.
- `clk_summary`: `pll_c` and `disp1` at 598 MHz; PLL_M/GPU rates unchanged.
- `/proc/interrupts` IRQ 21 (`tegradc.0`) advances.
- `lp855x` probe succeeds; `lcd-backlight` exists at brightness 128,
  max 255, power 0; `wingray_registers` A1=0x67, A2=0xbf.
- Operator sees the bootstrap colour pattern and/or Android UI.
- Android still reaches `sys.boot_completed=1` with the NVIDIA renderer.

## Limits

- The image retains cookie `0x584d0060`. Do not use Image 60's retained trace
  for this boot; collect the fresh USB report and dmesg instead.
- No flash, recovery write, repartition or Android filesystem write was
  performed during preparation. The device owner confirmed the original
  boot/recovery restoration before this preparation.
- Wi-Fi, Bluetooth, audio, charging control, DVFS and suspend are not added.
- A visible image alone does not prove HWC flip/fence correctness; inspect
  the report and, if needed, instrument the legacy flip path separately.
