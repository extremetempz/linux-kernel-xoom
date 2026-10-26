# Power-button candidate 76

26 October 2026. **Built and checked, not flashed or hardware validated.**
This candidate is based on the working Bluetooth 75b profile and adds the
reviewed Motorola CPCAP transport correction.

## CPCAP changes

- Wingray uses **active-low CS0** and SPI mode 0 again; `spi-cs-high` was
  removed from both Wingray CPCAP DT descriptions.
- Register access is one native-endian **32-bit full-duplex SLINK word**:
  command in bits 31:16, reply in bits 15:0.
- Existing CPCAP register constants already contain the legacy word-address
  shift; the patch does not shift a second time.
- The SPI bits-per-word is 32 for Wingray, 16 for other boards.
- The raw VERSC1 identity is logged before decoding. An invalid zero/all-ones
  reply now logs a warning and **continues booting**; it no longer turns a
  transport experiment into a display/Wi-Fi/Bluetooth boot failure.
- The ON-sense polling path, KEY_POWER mapping and volume-down fallback are
  unchanged.

## Image identity

- Path: `artifacts/androidpower76-ready/wingray-android44-gpu.img`
- Size: 4,130,816 bytes
- SHA-256: `dcb56016bc54c9d2cdc11b42a27d82aec67d24d846798a9db0a3a0f1dabe5086`
- Profile: Bluetooth 75b (Wi-Fi + Bluetooth + power transport)

## Checks

```text
PASS actual CPCAP functions: native32 full duplex, Motorola CS polarity,
     register vectors, errors, identity guard
PASS CPCAP power-key transport/config/DT scope
PASS actual Bluetooth power callback
PASS Bluetooth setup waits for UART, rfkill, HAL and firmware
PASS native 4.4 bcmdhd / WiFi
PASS compiled Bluetooth DT and configuration
```

The full ARM build and image packing pass.

## Flash and first test

Preserve 75b/73k and the recovery image first.

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidpower76-ready/wingray-android44-gpu.img
fastboot reboot
```

First confirm the image still boots with:

- display and touch
- Wi-Fi DHCP/Internet
- Bluetooth headphones

Then check the back power button. Capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidpower76-report1 \
  --storage-mode android44-readonly
```

Look for:

```text
Wingray CPCAP VERSC1=....
CPCAP vendor: ST rev: 1.0 (0)
CPCAP ON interrupt unmasked
CPCAP power key pressed
CPCAP power key released
```

A valid non-zero VERSC1 and ON-sense transitions are the transport success
criteria. KEY_POWER delivery to Android and screen behavior are the next
criteria. The CPCAP parent IRQ/GIC path and wake-from-suspend remain separate
work; polling is still the development fallback.

If the image fails to boot, restore 75b or 73k immediately.
