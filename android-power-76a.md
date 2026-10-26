# Power-button isolation candidate 76a — REJECTED

26 October 2026. **Physical result: screen flickered again.** Do not use.
The remaining suspect was the CPCAP controller/pin mapping, not CS polarity.

Image 76 changed two CPCAP variables at once:

1. `spi-cs-high` / CS polarity
2. 16-bit split transfers to native 32-bit full-duplex framing

The original Motorola 2.6 board source confirms active-low CS0 and the
32-bit transfer, but the working 4.4 image had been stable with CS high and
split 16-bit transfers. 76a keeps the **previously stable CS-high polarity**
and changes **only** the register framing to native 32-bit.

## Image identity

- Path: `artifacts/androidpower76a-ready/wingray-android44-gpu.img`
- Size: 4,128,768 bytes
- SHA-256: `80c8ff66846444206493e0f9973fc534aaf5d7f4a29d2890aabf70c2f16d1fcf`
- Profile: Bluetooth 75b + native32 CPCAP transfer, prior CS polarity

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

## First test — screen first

Restore 75b first if coming from the flickering 76 image:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidbluetooth75b-ready/wingray-android44-gpu.img
```

If you choose to test 76a:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidpower76a-ready/wingray-android44-gpu.img
fastboot reboot
```

Do not test the power button first. Watch the display for flicker. If it
flickers at all, stop and restore 75b; the native32/32-bit setup is the
remaining suspect. If it stays stable, check dmesg for `Wingray CPCAP
VERSC1=....` and press the back power button.

A future 76b should keep the old split-16-bit transport and only add
read-only VERSC1 logging; do not change PMIC writes and CS polarity together
again.
