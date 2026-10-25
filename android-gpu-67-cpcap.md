# Image 67: CPCAP PMIC power-key foundation

25 October 2026. Image 66 proved the volume-down interim wake key works, but
the real Xoom power button is wired to the CPCAP PMIC ON interrupt, not a
GPIO. Image 67 adds only the CPCAP transport and power-key input path.

## Changes

- Enable the Tegra20 SLINK SPI controller, APB DMA and CPCAP MFD core:
  - `CONFIG_SPI=y`
  - `CONFIG_SPI_TEGRA20_SLINK=y`
  - `CONFIG_DMADEVICES=y`
  - `CONFIG_TEGRA20_APB_DMA=y`
  - `CONFIG_MFD_CPCAP=y`
- Leave `CONFIG_REGULATOR_CPCAP` disabled. No battery, charger, regulator or
  suspend driver is enabled.
- Add a minimal SPI1/CPCAP node to the fixed-clock GPU base DT, including
  the `spid`/`spie`/`spif` SPI1 pinmux. The early-boot include deliberately
  omits the full peripheral set, so this path must be explicit.
- Register CPCAP's ON interrupt as a `KEY_POWER` input device on Wingray:
  - second 16-bit interrupt bank, bit 7 (`CPCAP_IRQ_ON`),
  - raw sense state is reported as the key value,
  - the input device is wakeup-capable.
- If CPCAP or its IRQ is unavailable, log a warning and keep the Image 66
  screen-awake and volume-down fallbacks.
- Add `/proc/bus/input/devices` to the display report so the new input device
  can be verified.

## Image identity

- Path: `artifacts/androidgpu67-ready/wingray-android44-gpu.img`
- Size: 3,698,688 bytes
- SHA-256: `637660babda13f98d76a96b568bd92cc9a625f3549bd328a72e962bb94e9303b`
- Kernel patch: `0116-wingray-cpcap-power-key.patch`

## Hardware test

Flash boot only:

```sh
fastboot flash boot artifacts/androidgpu67-ready/wingray-android44-gpu.img
fastboot reboot
```

Verify before touching anything else:

1. The tablet still boots to the launcher and the display remains usable.
2. `dmesg` records CPCAP detection and `CPCAP power key registered`.
3. `/proc/bus/input/devices` contains `cpcap-pwrkey` with `KEY_POWER`.
4. Pressing the actual power button blanks/wakes Android.
5. No IRQ storm, repeated CPCAP errors, or boot hang.
6. Touch, display and USB diagnostics still work.
7. Volume-down still wakes as a fallback.

Capture a report after interacting:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu67-report1 \
  --storage-mode android44-readonly
```

The report includes `XOOM_INPUT_DEVICES`, full dmesg/interrupts and the
screen-awake log.

## Failure handling

Image 67 is the first image that probes CPCAP. If it hangs or regresses boot,
reflash Image 66 boot and capture the failing report/serial output:

```sh
fastboot flash boot artifacts/androidgpu66-ready/wingray-android44-gpu.img
fastboot reboot
```

Do not flash the original backup until the test is finished; keep
`artifacts/hardware-private/backup-boot.img` untouched.

## Not included

- battery, charger, fuel gauge and `healthd` power_supply reporting;
- Wi-Fi/BCM4329;
- Bluetooth/BCM4329;
- suspend/resume and full power management;
- HWC overlay composition.

Battery percentage will remain 0% in this image. That is expected because no
`power_supply` driver is enabled.
