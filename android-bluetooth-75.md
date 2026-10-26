# Bluetooth working image 75b

26 October 2026. **Hardware validated:** the user paired and connected a Sony
WH-1000XM5 headset on 75b. The Wi-Fi link stayed connected at the same time.
The 73k Wi-Fi image remains the default baseline; Bluetooth is an opt-in
profile.

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

## Hardware evidence

- Setup log: `READY_for_manual_Android_Bluetooth_toggle_NOT_hardware_validated`
- `rfkill0`: `bcm4329 Bluetooth`, soft/hard blocked 0
- `/dev/ttyHS2`: present, owned by UID/GID 1002, HCI traffic seen
  (`tx:3599 rx:10228 RTS|CTS|DTR`)
- `com.android.bluetooth` process and `BluetoothAdapterService` running
- `bcm4329.hcd`, `bluetooth.default.so` and `libbt-vendor.so` present
- Wi-Fi remained connected (`git gud`, DHCP/Internet) while Bluetooth was on

Pairing/connection is confirmed. Audio routing (A2DP/SCO), microphone,
reconnect after suspend, and long Wi-Fi coexistence remain separate tests.

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

## Remaining hardware tests

1. Test A2DP audio, headset microphone/SCO, and reconnect after suspend.
2. Toggle Bluetooth and Wi-Fi repeatedly while Wi-Fi carries traffic.
3. Validate the factory BD address path and multi-device pairing.

The captured report was taken before the headset name appeared in the
bounded `dumpsys bluetooth_manager` section, so the connection evidence here
is the user-observed pairing plus ttyHS2 traffic and the running Bluetooth
service. To capture the paired name, wait for the headset connection and use:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidbluetooth75b-report2 \
  --storage-mode android44-readonly
```

Awake-only limits remain: no host-wake IRQ, UART LPM, suspend/resume, BLE
or long coexistence validation.
