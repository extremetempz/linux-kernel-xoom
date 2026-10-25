> **Superseded by Image 67c.** Report 1 showed the input device exists but
> neither CPCAP IRQ counts when the button is pressed. Use
> `android-gpu-67c-cpcap-poll.md` for the polling fallback.

# Image 67b: accept Wingray CPCAP 1.0 revision

25 October 2026. Image 67's first hardware report identified the exact reason
the real power button still produced no input:

```text
cpcap-core spi32766.0: CPCAP vendor: ST rev: 1.0 (0)
cpcap-core spi32766.0: Please add old CPCAP revision support as needed
cpcap-core spi32766.0: Failed to detect CPCAP: -19
```

The SPI transport worked, but the mainline CPCAP core rejects every revision
below 2.1. The Xoom's ST part reports raw revision zero, which the core prints
as 1.0. The ON interrupt and the registers used by this image are compatible;
the regulator/charger drivers remain disabled.

## Fix

`cpcap_check_revision()` now accepts raw revision zero and the explicit 1.0
encoding, while retaining the existing floor for other old revisions. No other
CPCAP, IRQ, pinmux or input mapping changed from Image 67.

Kernel patch: `0117-wingray-cpcap-rev10.patch`

## Image identity

- Path: `artifacts/androidgpu67b-ready/wingray-android44-gpu.img`
- Size: 3,698,688 bytes
- SHA-256: `6e3de2f754f72d04444663d4dd5db7cc4ae1980006eb12a53aa2b0d66457944d`

## Hardware test

Flash boot only:

```sh
fastboot flash boot artifacts/androidgpu67b-ready/wingray-android44-gpu.img
fastboot reboot
```

Expected dmesg sequence:

```text
CPCAP vendor: ST rev: 1.0 (0)
CPCAP power key registered
input: cpcap-pwrkey ...
```

Then:

1. `/proc/bus/input/devices` contains `cpcap-pwrkey` with `KEY_POWER`.
2. The actual back power button blanks/wakes Android.
3. No repeated CPCAP errors or IRQ storm.
4. Volume-down still wakes as fallback.
5. Display, touch and USB diagnostics still work.

Capture while/after pressing the power button:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu67b-report1 \
  --storage-mode android44-readonly
```

If CPCAP now probes but the key still does not fire, the next evidence needed
is the post-probe dmesg, the `cpcap` line in `/proc/interrupts`, and whether
the `cpcap-pwrkey` input device exists. Do not jump to pinmux changes before
those three are known.

## Failure handling

If Image 67b does not boot or regresses, reflash Image 66:

```sh
fastboot flash boot artifacts/androidgpu66-ready/wingray-android44-gpu.img
fastboot reboot
```

Image 67b still contains no battery/charging, Wi-Fi, Bluetooth, suspend or HWC
overlay work. Battery remains 0%, expected.
