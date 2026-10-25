# Image 71c: capture why wpa_supplicant exits

25 October 2026. 71b finally got the driver and timing right:

```text
boot_delay=40
dhd_module_init @ 42.637
register interface [wlan0]
Firmware version ... 4.218.248.44
wlan0 present
```

But supplicant still times out, and WifiStateMachine repeatedly returns to
InitialState. The wrapper log contained only:

```text
wpa wrapper: bringing wlan0 up
ifconfig_rc=0
```

with no `wpa_supplicant` diagnostics, because Android's supplicant logs to
logcat, not stdout, even with `-f`.

Image 71c:

- removes `-f` from the supplicant command
- runs `logcat -d -v time -s wpa_supplicant:*` after three seconds into
  `/run/wpa-logcat.txt`
- includes that file in the diagnostic report

Everything else is unchanged: TF101 bcmdhd 5.90.125.94, AOSP firmware,
PMOS NVRAM, platform-device bypass, 40-second load, regulatory fix.

## Image identity

- Path: `artifacts/androidgpu71c-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `656c8ee319aba5746aefdf9755f5f8f528984d51e6615084388336aa7be1a4cd`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu71c-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu71c-report1 \
  --storage-mode android44-readonly
```

The report's `WPA_LOGCAT` will show the exact supplicant driver/control
socket error. Recovery remains 70t or Image 66.
