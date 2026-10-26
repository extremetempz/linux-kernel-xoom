# Wingray P3 battery/charger monitor — image 79 built, NOT flashed

26 October 2026. Root baseline: main `d14be8f`. This is an opt-in,
monitoring-only Linux 4.4.147 / Android 4.4.4 candidate, not a hardware pass.
No device was accessed and no boot, recovery, partitions or live settings
were modified. Audio, suspend/resume, DVFS and CPCAP transport were untouched.

## Hardware identification changes the proposed implementation

The requested original Motorola branch resolves to
[`6b3d70fff905b7395fd15992c3779b27d1b6c101`](https://github.com/Schischu/android_kernel_moto_wingray/tree/6b3d70fff905b7395fd15992c3779b27d1b6c101).
Its BQ20Z75 source file exists, but **board-stingray does not register it**.
The actual battery path is DS2781 via Tegra OWR/1-Wire. Saved original-ROM
logs identify `ds2781-battery`; saved original boot arguments identify
`hw_rev=p3`. These are previously collected device observations, not a new
live measurement. There is no verified BQ20Z75 I2C controller/address to enable.

Sources examined:

- [Original board](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/arch/arm/mach-tegra/board-stingray.c): OWR initialization/timings, BQ24617 resources and revision-specific inputs.
- [Original resources](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/arch/arm/mach-tegra/devices.c) and iomap.h: OWR `0x7000c600`, length `0x50`; INT_OWR is GIC SPI 30. Existing 4.4 clock/reset ID 71 supplies OWR.
- [Original pinmux](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/arch/arm/mach-tegra/board-stingray-pinmux.c): OWC selects OWR, pull-up, non-tristate.
- [Original DS2781 policy](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/drivers/power/ds2781_battery.c): real RARC capacity and measurement scaling; includes write/calibration/full-detection policy deliberately not imported.
- [Original BQ24617 monitor](https://github.com/Schischu/android_kernel_moto_wingray/blob/6b3d70fff905b7395fd15992c3779b27d1b6c101/drivers/power/bq24617_charger.c): STAT and DETECT truth table.
- board-stingray-power.c and cpcap-adc.c: PMIC power/ADC infrastructure exists, but is unnecessary for reading DS2781 percentage. No CPCAP ADC subsystem or regulator/charger control was enabled.

For this P3 tablet: PV5/173 STAT1, PD1/25 STAT2, PV6/174 DETECT.
The saved original GPIO list confirms these input labels. Older P0 boards
use PV6 for STAT2 without independent detection; that layout is **not**
claimed supported. Charger-disable PS7/151 and charge-LED PV0/168 remain
untouched. The driver fails if status inputs are already owned; it never
steals a GPIO or toggles an enable output.

## Minimal reuse and read-only policy

The 4.4 tree contains the power_supply core, SBS/BQ20Z75-compatible support,
DS2781 W1 family and a generic DS2781 battery driver. It lacks Tegra OWR and
BQ24617 support. Existing Tegra I2C support is not the missing battery bus.

- Port Motorola's OWR driver to device-tree/4.4 clock and reset APIs, retaining its original timings and register sequences. Bound completion waits, initialize completion before enabling IRQs, propagate bit failures through short block reads, and unregister clients before releasing the controller.
- Reuse the existing 4.4 DS2781 W1 family. Fix its reset/select failure path, which previously could report success without reading data. Opt-in Wingray monitoring blocks memory writes and all EEPROM commands before bus IO.
- Keep the generic DS2781 battery driver disabled: it exposes writable calibration, control and EEPROM attributes, and its read conversions require signed-byte/precision fixes. Instead add a small Wingray-only power_supply consumer using the same DS2781 transport and Motorola register definitions.
- Publish `battery` and `ac` standard supplies, polling every two seconds. Charger GPIOs are requested as inputs only. No charger IRQ, PMIC mask/ack, enable pin, EEPROM or calibration writes are used. Protocol command/address bytes required to READ the gauge and OWR controller MMIO setup are not gauge configuration writes.
- Failed or short reads return errors, never cached fabricated values. Initial transient reads remain retryable; Android startup waits up to 30 seconds for readable supplies, otherwise stays in diagnostic userspace with USB available.

### Measurement definitions

| Property | Source / conversion |
|---|---|
| capacity | DS2781 RARC at 0x06, actual 0–100%; outside range is an error, never clamped or voltage-estimated |
| voltage_now | 0x0c/0x0d upper 11 bits × 9760 microvolts, as Motorola; zero/out-of-range rejected |
| temp | signed 0x0a/0x0b fixed-point value × 0.125 C, converted to tenths C |
| current_now | signed 16-bit 0x0e/0x0f × 1.5625 × factory RSNSP conductance at 0x69, in microamps; final division preserves precision; positive means charging |
| present | 1 only after valid gauge reads; read errors remain errors, not a made-up presence claim |
| status | Independent BQ24617 input truth table below |
| health | Omitted: no validated complete fault/health decoder; Android keeps unknown |

No ACR resets, factory sense-resistor writes, charging limits, temperature
protection changes or legacy host-side charge recalibration were imported.
The existing gauge configuration must already be valid. Zero RSNSP makes
current unavailable (`ENODATA`) without hiding valid percentage/voltage.
Long-term accuracy without the original host recalibration policy still
requires real monitoring; this work does not assume it from compilation.

### Charger truth table (raw input levels)

`online = !STAT1 || !STAT2 || DETECT`, matching Motorola.

| STAT1 | STAT2 | DETECT | AC online | Battery status |
|---|---|---|---|---|
| 1 | 1 | 0 | 0 | Discharging |
| 1 | 1 | 1 | 1 | Not charging |
| 0 | 1 | either | 1 | Charging |
| 1 | 0 | either | 1 | Full |
| 0 | 0 | either | 1 | Unknown: contradictory STAT signals |

Charger connection alone never means charging. No status forces capacity to
100. Contradictory detection/STAT signals should be saved in a report, not
"fixed" by changing pin polarity. Polling avoids adding new interrupt handling
while the pre-existing CPCAP IRQ problem is outside this task's scope.

## Android 4.4 integration

Reviewed [KitKat BatteryMonitor.cpp](https://android.googlesource.com/platform/system/core/+/android-4.4.4_r2/healthd/BatteryMonitor.cpp)
and healthd.cpp/h. healthd discovers supplies by `type`, reads battery
capacity/status/present/voltage_now/temp/current_now, and discovers AC online
from a Mains supply. Voltage is converted from microvolts to Android millivolts;
temperature remains tenths C. Power-supply uevents trigger updates.
The original saved ramdisk's healthd binary also contains `/sys/class/power_supply`
and the power_supply event filter, with no observed hard-coded battery subpath.
No framework/HAL replacement or fake battery setting is added.

Because healthd discovers paths once, only the opt-in battery profile waits
for readable battery/ac supplies before exec of Android init. Ordinary profiles
skip this wait. Actual installed healthd discovery, uevent delivery and UI
updates remain hardware-test gates.

## Reproducible patch/build changes

- **0142:** export already-existing local `fcb5c581` volume-key retirement, previously documented but missing from main's patch series. Build 78 itself still contains the fallback; this candidate restores normal volume keys as requested previously.
- **0143:** Motorola OWR port plus DS2781 transport/read-only guards.
- **0144:** separate P3 monitoring driver, DT and battery defconfig.
- **0145:** allow retry after initial gauge-read failure, plus whitespace cleanup.

`wingray_android44_battery_defconfig` inherits Bluetooth/GPU/Wi-Fi features.
Resolved 78→79 config differences are only selected DT and W1/power_supply
monitoring dependencies. Sound, suspend, CPU scaling and CPCAP regulators stay
disabled. Compiled DT comparison against 78 finds only the new monitoring
nodes and the documented volume-key restoration. CPCAP bus, CS, pinmux,
frequency and driver bytes are unchanged. No Samsung power tables were added.

Build with saved private ROM references and the pinned toolchain available:

```sh
XOOM_ANDROID_GPU_PROFILE=battery \
XOOM_BUILD_ROOT=/tmp/xoom-battery79-clean \
XOOM_ARTIFACT_DIR="$PWD/artifacts/androidbattery79-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/androidbattery79-ready" \
bash scripts/build-android-gpu.sh
```

Use fresh, nonexistent artifact directories when rebuilding. There are no
device commands in this build process. Private original-ROM inputs are local
only and are not committed or bundled as new proprietary libraries.

## Available validation — passed offline

- Full ARM kernel and bcmdhd module build, link, compression, appended battery DT, built-in runtime and Android boot-image packing.
- Complete 145-patch series applies to pinned donor. Monitoring source/config/DT match the built donor. Two older pre-existing GPU defconfig files differ only by an obsolete disabled LEGACY_BCMDHD line; the battery config is identical.
- Actual-function host tests: all eight GPIO combinations, signed units, short/error reads, invalid capacity/voltage, unavailable current, initial AC property access before pointer assignment, EEPROM/write rejection, unchanged other-board write path, and Tegra block-error propagation.
- Compiled DT/config gates and negative controls reject changed charger GPIO, OWR controller, OWR pull and CPCAP frequency; normal volume keys checked.
- Existing CPCAP key/transport, Bluetooth power/setup/compiled-DT, native Wi-Fi and inherited GPU compiled-DT/config gates pass. The old image-59 test with a hard-coded missing build directory was not a usable current validation target; current `android_gpu.validate_artifacts` was run instead.
- Python syntax, shell syntax and source whitespace checks. No new-driver compilation warnings; inherited graphics code has an existing unused-function warning.

## Prepared image identity

- `artifacts/androidbattery79-ready/wingray-android44-gpu.img`
- 4,145,152 bytes
- SHA-256 `580cb7a243d5274bd455ae520e3af879b53fe98e3db1dc11a467ed1645c9e135`
- Kernel source head: `777a6b1f` (source patches 0143–0145 plus prior fallback retirement).
- **Test A hardware-validated:** charger disconnected reports 62%, 7.64208 V,
  -358906 uA, 27.5 C, Discharging and ac offline; Android BatteryService shows
  level 62 and healthd is running.
- **Test B hardware-validated:** charger connected reports ac online 1,
  61%, Charging, 7.97392 V, +1.529531 A, 27.7 C; Android reports AC powered,
  status 2 and level 61. See [Test A](battery-79-testA.md) and
  [Test B](battery-79-testB.md).
- **Test C/D evidence missing:** no post-disconnect report3 exists yet; the
  B→C transition and extended monitoring are not captured. Full/not-charging
  states and the charging icon should be confirmed in that capture.
- Preserved 78 image SHA-256 remains `e8a698405f65b9a6b408d66bbf864662bf9830cdc155670d4808474f60dee49d`.

The PR's earlier image hash `2b9faae1…` was not the actual local build: that build
script omitted `tegra20-motorola-wingray-android44-battery.dtb` from the make
and copy steps. The corrected build includes the battery DTB and produces the
hash above. The bootstrap also now logs `WARN_battery_monitor_missing` and
continues to Android instead of refusing to boot if the monitor does not
enumerate.

## Hardware test protocol — only after explicit flash approval

Preserve original boot/recovery and known-good 78 image and hashes first.
Use the established boot-only test/restoration procedure; never repartition,
write recovery, or flash automatically. Keep a way to return to fastboot.
This profile reads the existing system read-only and uses tmpfs data/cache.

The USB Android report includes `/bin/battery-report`: power_supply devices,
properties and read failures, charger-input ownership, OWR/CPCAP interrupt
counts, relevant kernel/I2C errors, healthd logs and Android dumpsys battery.
It writes no settings or hardware registers. Record a fresh report per stage:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidbattery79-testA \
  --storage-mode android44-readonly
```

Use a new output directory for each capture. Save reports privately because
inherited Android/Wi-Fi/Bluetooth sections can contain identifiers.

1. **A / disconnected:** capture after startup and two polling periods. Check real 0–100 gauge capacity, plausible voltage/temperature, signed current where available, `ac/online=0`, battery Discharging, and Android dumpsys/status bar agreement. Do not deep-discharge.
2. **B / connected:** attach the original compatible wall charger, wait at least two polling periods, capture again. AC must become online. Status should reflect STAT1/STAT2: charging, naturally full, or connected/not charging. Verify Android indication agrees, not merely presence. Do not force charging or wait unattended for full.
3. **C / disconnected again:** capture after two polling periods. Confirm offline/discharging and Android update without reboot. Repeat several times, recording any transition glitch instead of changing polarity on assumption.
4. **D / extended:** take private snapshots every 30–60 seconds during ordinary use, both plugged and unplugged. Compare voltage/current/temperature/percentage and read failures over time, including natural percentage movement. Check OWR errors/IRQ progress and kernel stability. Reads use the actual DS2781, so BQ20Z75 I2C errors are not expected; unrelated I2C errors are still collected.
5. **Regressions:** Android boot, NVIDIA renderer/display without flicker/underflow, real touch, Wi-Fi Internet, Bluetooth connection, physical power key short/long press and display on/off, normal volume keys, USB diagnostics, two CPUs/PL310 and matching BigPart extents. Do not introduce audio, deep suspend or DVFS tests.

The existing build-78 CPCAP interrupt storm/IRQ disable is a known baseline
problem even though polling provides the power button. It was not fixed or
silently reclassified as healthy by this monitoring work. New OWR interrupts
occur per 1-Wire bit; bounded measurement activity is expected, an unhandled
IRQ storm is not. Restore the known-good image if new errors or regressions
appear, then verify the preserved images using the established procedure.

Definition of success remains the physical A–D measurements and regression
checks. Compilation and these simulated hardware faults do not satisfy it.
