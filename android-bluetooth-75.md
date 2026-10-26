# Bluetooth candidate 75b

26 October 2026. **Not flashed and not hardware validated.** The working
73k Wi-Fi image remains the hardware-tested baseline.

This iteration hardens the opt-in Bluetooth profile on top of the PR's 74b
candidate:

- `bluetooth-setup` now waits up to 60 seconds for **all** prerequisites:
  `/dev/ttyHS2`, the `bcm4329 Bluetooth` rfkill, the Android Bluetooth HAL,
  the vendor library and `bcm4329.hcd`.
- It is triggered both at `boot` and at `sys.boot_completed=1`, so a
  transient early boot miss is retried instead of leaving the service dead.
- The rfkill callback now waits 20 ms after enabling the shared Wi-Fi/BT rail
  and 20 ms after releasing reset.
- Duplicate `CONFIG_RFKILL` defconfig entries were removed.
- The package manifest identifies `android44-bluetooth` rather than
  `android44-gpu`.
- New tests cover the setup wait/retry path and the delayed power callback.

## Image identity

- Path: `artifacts/androidbluetooth75b-ready/wingray-android44-gpu.img`
- Size: 4,128,768 bytes
- SHA-256: `511447ee0fcda81c71c5ca5c7e8e7da9590da8e50ebb9a6cd09cacc83599263b`
- DT: `tegra20-motorola-wingray-android44-bluetooth`
- Kernel: native 4.4 bcmdhd plus built-in `rfkill-wingray-bt`
- `CONFIG_BT` remains off: Android's Broadcom vendor HAL owns HCI/firmware
  over `ttyHS2`

## Offline checks

```sh
python3 tests/test-wingray-bluetooth-power.py
python3 tests/test-wingray-bluetooth-profile.py artifacts/androidbluetooth75b-runtime
python3 tests/test-wingray-bluetooth-setup.py
python3 tests/test-wingray-wifi.py
```

All four pass. The full ARM build and image packing pass. The exported
`kernel/patches/0140-wingray-bluetooth-awake-profile.patch` applies to the
pinned donor.

## Hardware test gates

1. Preserve 73k and the recovery image; flash only this boot candidate.
2. Boot with Bluetooth still blocked and verify display, touch, SMP, storage
   and **73k Wi-Fi with DHCP/Internet**.
3. Check `/run/xoom-bluetooth-setup.log` and the `XOOM_BLUETOOTH` report:
   `ttyHS2`, the correct rfkill, HAL/vendor library and HCD.
4. Enable Bluetooth in Settings, wait 20 seconds, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidbluetooth75b-report1 \
  --storage-mode android44-readonly
```

5. Only after controller startup is confirmed, test discovery, pairing,
   transfer and a Bluetooth/Wi-Fi coexistence toggle.

Awake-only limits remain: no host-wake IRQ, UART LPM, suspend/resume,
audio/SCO, BLE or long coexistence validation. A successful boot with
Bluetooth still blocked is **not** Bluetooth success.
