# Bluetooth preparation on the working 73k baseline

26 October 2026. **No flashing, reboot or Bluetooth radio operation was
performed. Bluetooth is not yet hardware validated.** The preserved baseline
is public main `60cfb5f7f0aa019cfddac14cc9329683ae181f15`, including the
hardware-tested 73k Wi-Fi route. Its image and recovery candidates are unchanged.

## Findings and reuse

The Wi-Fi work established that the working firmware/userspace contract
matters more than simply enabling a same-chipset driver. This stage therefore
reuses the donor's existing `serial-tegra` UART driver and the installed
Android Broadcom vendor HAL/firmware. It does not import a Samsung board or
replace the working Wi-Fi driver with a legacy alternative.

Motorola's `board-stingray-bluetooth.c` identifies:

| Signal | Original Motorola wiring | This profile |
|---|---|---|
| UART | UARTC, original `/dev/ttyHS2` | `nvidia,tegra20-hsuart`, serial2 alias, native `serial-tegra` still names ports `ttyHS` |
| Reset release | PU0 | Low while blocked, high after acquiring power |
| Shutdown | PI7 | Low in both states, matching original Motorola code |
| Device wake | PU1 | Held high while unblocked; awake-only bring-up |
| Host wake | PU6 | Input only; no floating IRQ enabled while blocked |
| Shared combo enable | PU4 | Existing `/wlan-power` regulator; independent reference for Bluetooth |

The original `change_power_brcm_4329()` reference-counts the common Wi-Fi/BT
rail. The new small board adapter replaces only that legacy board plumbing
with Linux regulator references and GPIO descriptors. It does not drive PU4
itself, reset Wi-Fi on PU2, modify Wi-Fi pinmux or change display clocks.
The regulator's already tested startup delay is retained. The generic
`rfkill-gpio` helper cannot directly express Motorola's shutdown-low-in-both-
states sequence and lacks this DT/shared-regulator handling in this kernel.

A second blocker was in the Android RAM overlay: it copied graphics/default
HALs into `/system/lib/hw` but omitted `bluetooth.default.so`. The opt-in
Bluetooth profile now includes that original HAL before the overlay becomes
read-only. The vendor library and `bcm4329.hcd` remain on the existing
read-only system partition; no proprietary binaries are committed.

Original 73k private report records `/system/etc/firmware/bcm4329.hcd`
(17,909 bytes). No device is currently attached over ADB, so the actual
installed vendor-library location, its build options and factory Bluetooth
address have **not** been independently checked during this stage.

## Separate implementation

- Kernel patch `0140-wingray-bluetooth-awake-profile.patch`: small Motorola
  rfkill adapter, binding, dedicated DT and dedicated defconfig.
- New profile `XOOM_ANDROID_GPU_PROFILE=bluetooth`; default remains `fbmap`.
- UARTC selects the existing native driver; Linux `CONFIG_BT` remains off
  because Android Bluedroid owns raw HCI UART and firmware download. No
  competing kernel HCI line discipline is attached.
- `bluetooth-setup.sh` waits for ttyHS2, discovers the Bluetooth rfkill by type
  and name rather than assuming rfkill0, and grants only Bluetooth UID/GID
  access. It checks HAL/vendor-library/firmware availability. It does not
  unblock the radio, enable Bluetooth settings or download firmware itself.
- `bluetooth-report.sh` adds bounded read-only diagnostics under the existing
  verified read-only system-report guard. Raw reports remain private.
- Packaging validates the compiled Bluetooth DT against the existing fbmap
  DT, resolving phandles and preserving GPIO arguments. Only Bluetooth
  nodes, UARTC configuration, the serial2 alias and model may differ.

## Offline validation

- Full ARM kernel, native serial-tegra, board rfkill adapter, DT and native
  bcmdhd module compile and link.
- Actual rfkill callback is compiled and executed with injected regulator
  enable/disable failures, repeated state changes and a simulated independent
  Wi-Fi power vote. A failed disable followed by re-enable reasserts wake/reset
  without leaking another rail reference.
- Compiled DT comparison passes. Negative controls reject altered Wi-Fi
  power, display clock and Bluetooth reset wiring.
- Existing `tests/test-wingray-wifi.py` passes unchanged.
- Static runtime helpers are rebuilt for this kernel configuration. Packaging
  checks archive equality, kernel/DT matching and the 8 MiB boot limit.

Build with the existing private ROM/runtime references and pinned toolchain:

```sh
XOOM_ANDROID_GPU_PROFILE=bluetooth \
XOOM_ARTIFACT_DIR="$PWD/artifacts/androidbluetooth-new-runtime" \
XOOM_IMAGE_DIR="$PWD/artifacts/androidbluetooth-new-ready" \
bash scripts/build-android-gpu.sh
python3 tests/test-wingray-bluetooth-power.py
python3 tests/test-wingray-bluetooth-profile.py artifacts/androidbluetooth-new-runtime
python3 tests/test-wingray-wifi.py
```

## Hardware gates for a later, separately scheduled test

1. Preserve and verify the original boot/recovery plus the working 73k
   candidate; check battery/power and prepare a recoverable boot-only cycle.
2. Boot the separate candidate, first verify display/touch/SMP/storage and
   73k Wi-Fi DHCP/Internet remain functional with Bluetooth still blocked.
3. Read `XOOM_BLUETOOTH` diagnostics: ttyHS2 present, correct rfkill state,
   vendor HAL/library and original HCD available. Validate the factory address
   path; do not invent a shared or fixed MAC address.
4. Manually enable Android Bluetooth. Capture vendor logs and HCI startup
   before concluding firmware download/controller initialization succeeded.
   Confirm the actual vendor baud rate: Motorola and this Tegra20 UART path
   use the retained 600 MHz UARTC source with an integer divisor. Broadcom
   upstream defaults to 3 Mbaud, but the installed HAL's setting is unknown;
   do not change shared PLL_M/EMC to compensate for an unverified baud.
5. Test discovery, pairing and a real data/input transfer, then independent
   Bluetooth/Wi-Fi toggles while Wi-Fi carries traffic. Confirm disabling
   Bluetooth leaves Wi-Fi connected and releases only its own power vote.
6. Restore/verify the selected recovery baseline after the controlled test.

The held-high device-wake approach is deliberately an awake-only first step.
Host-wake IRQs, UART low-power callbacks, suspend/resume, power consumption,
SCO/A2DP/audio routing, BLE capabilities and long coexistence tests remain
separate gates. Holding wake does not prove the installed firmware's LPM
protocol compatible. Bluetooth success cannot be claimed from this build.

References: Motorola/Google original GPL board source; donor serial-tegra;
[Android KitKat Broadcom vendor HAL](https://github.com/LineageOS/android_hardware_broadcom_libbt/tree/cm-11.0),
reviewed at revision `bbb55397b562c915464282224743ba4d92bf50f3`. No new firmware
loader or HCI stack was invented.

## Completed candidate

The full documented build script passed without device access. Final candidate
is `artifacts/androidbluetooth74b-ready/wingray-android44-gpu.img`,
4,124,672 bytes, SHA-256
`e8595162a15f60ffa9327c60bb2284ee6b40c2bd104195951de3cf29b799a512`.
An earlier intermediate 74 build is retained separately; use 74b for a later
controlled test. Both remain unflashed. See
[build checks](bluetooth-74-build-checks.json). Proprietary-containing boot
images stay local; source, patch, checks and sanitized findings are published.
