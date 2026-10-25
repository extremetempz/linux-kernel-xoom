> **Superseded by Image 67d.** The 67c report showed `initial sense=0` and
> no transitions. Image 67d explicitly unmasks ON and logs raw INT2/INTS2.
> Use `android-gpu-67d-cpcap-key-raw.md`.

# Image 67c: poll the CPCAP ON sense bit for the power key

25 October 2026. Image 67b fixed CPCAP identification and created the
`cpcap-pwrkey` input device, but the physical back power button still did not
work. Report 1 shows why:

```text
N: Name="cpcap-pwrkey"
...
80: 0 0 cpcap-m2 7 Edge cpcap-pwrkey
56: 0 0 LIC 86 Level cpcap-m2, cpcap-m2, cpcap1-4
```

The input device exists, but neither the CPCAP parent IRQ nor the nested
power-key IRQ ever counted an interrupt while the button was pressed. SPI
reads still work (the SPI IRQ count increases), so the problem is the CPCAP
interrupt line/mask/trigger path, not the input registration.

## Workaround

Instead of waiting for the missing IRQ, a delayed work item polls
`CPCAP_REG_INTS2` bit 7 (the ON sense bit) every 50 ms. It reports
`KEY_POWER` on state changes and logs:

- the initial sense value at registration,
- `CPCAP power key pressed`,
- `CPCAP power key released`.

This is a development fallback, not a fix for the CPCAP interrupt path. It is
limited to the Wingray power key; the CPCAP IRQ core remains registered for
other users.

Kernel patch: `0118-wingray-cpcap-key-poll.patch`

## Image identity

- Path: `artifacts/androidgpu67c-ready/wingray-android44-gpu.img`
- Size: 3,698,688 bytes
- SHA-256: `15bbcc02b02e202bd72db9646d7978b7600775e326074394ab58163aee49bef5`

## Hardware test

Flash boot only:

```sh
fastboot flash boot artifacts/androidgpu67c-ready/wingray-android44-gpu.img
fastboot reboot
```

Expected dmesg at boot:

```text
CPCAP power key initial sense=0
CPCAP power key polling registered
```

Then press and release the back power button. Expected dmesg:

```text
CPCAP power key pressed
CPCAP power key released
```

The display should blank on the press and wake on the next press (or follow
Android's normal power-key behavior). Capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu67c-report1 \
  --storage-mode android44-readonly
```

### If there are no pressed/released messages

- `initial sense` value plus no transitions means the button is not changing
  INTS2 bit 7. The next step is to inspect the raw INTS2 value and the ON2/
  other CPCAP interrupt-sense bits; do not change the input mapping blindly.
- The report still includes `/proc/interrupts`, dmesg and the input list.

## Scope

Still only the CPCAP power-key foundation. No battery/charging, Wi-Fi,
Bluetooth, suspend or HWC overlay work. Battery remains 0%, expected.

Image 66 remains the fallback:

```sh
fastboot flash boot artifacts/androidgpu66-ready/wingray-android44-gpu.img
```
