> **Superseded by Image 67e.** The DT routed `GIC_SPI 86` through the Tegra
> LIC instead of the GIC. Image 67e fixes the parent and keeps the all-bank
> diagnostic. Use `android-gpu-67e-cpcap-gic.md`.

# Image 67d: unmask CPCAP ON and capture raw key registers

25 October 2026. Image 67c report:

```text
CPCAP power key initial sense=0
CPCAP power key polling registered
```

No pressed/released messages. SPI polling works, but INTS2 bit 7 never
changed while the physical button was pressed. The mainline regmap IRQ core
masks all interrupt sources at registration, and Image 67c did not request
the ON virtual IRQ, so the mask was never cleared.

## Changes

- Explicitly unmask the CPCAP ON source in `INTM2` and clear stale `INT2`
  status before polling.
- Poll at 20 ms instead of 50 ms, so a short press is less likely to be
  missed.
- Log the full `INTS2` and `INT2` values whenever they change.
- Continue reporting `KEY_POWER` from INTS2 bit 7.

This is both an attempted fix for the masked source and the diagnostic needed
to identify the real button bit if bit 7 still does not move.

Kernel patch: `0119-wingray-cpcap-key-raw.patch`

## Image identity

- Path: `artifacts/androidgpu67d-ready/wingray-android44-gpu.img`
- Size: 3,698,688 bytes
- SHA-256: `b8d824b1f97970a6d48ef72df2bc38f6fb9166a3e05cfc7e6ee205b1bcf65b22`

## Hardware test

Flash boot only:

```sh
fastboot flash boot artifacts/androidgpu67d-ready/wingray-android44-gpu.img
fastboot reboot
```

At boot, expect:

```text
CPCAP ON interrupt unmasked
CPCAP power key initial INTS2=0000 sense=0
CPCAP power key initial INT2=....
CPCAP power key polling registered
```

Press and release the back power button several times, including a long
press. Then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu67d-report1 \
  --storage-mode android44-readonly
```

Expected if the ON path works:

```text
CPCAP INTS2=0080
CPCAP power key pressed
CPCAP power key released
CPCAP INTS2=0000
```

## Interpretation

- `INTS2` changes at bit 7 → the button and PMIC sense path work; the key
  events should now sleep/wake Android.
- `INTS2` changes at another bit → that is the actual power-button bit; map
  it next.
- `INT2` changes but `INTS2` does not → the status path is latching but the
  sense register is not updating; use the status bit next.
- Neither changes on multiple presses → the button is not reaching CPCAP
  bank 2; the next step is to identify the physical GPIO/PMIC input rather
  than guessing.

## Risk

Unmasking ON can expose a stuck CPCAP interrupt line. If the tablet boots
poorly or shows an IRQ storm, reflash Image 66:

```sh
fastboot flash boot artifacts/androidgpu66-ready/wingray-android44-gpu.img
```

No battery/charging, Wi-Fi, Bluetooth, suspend or HWC overlay changes are
included.
