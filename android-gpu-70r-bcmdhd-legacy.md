> **Superseded by Image 70s.** 70r only captured wpa debug; 70s adds the
> postmarketOS BCM4329 NVRAM required by the firmware. Use
> `android-gpu-70s-bcmdhd-legacy.md`.

# Image 70r: capture wpa_supplicant's file log

25 October 2026. Image 70q finally used the postmarketOS/AOSP firmware path:

```text
sta_fw=aosp_246791:246791
ifconfig_rc=0
```

The wrapper brought `wlan0` up successfully, but `wpa_supplicant` still
failed interface initialization:

```text
WPA_LOG
wpa wrapper: bringing wlan0 up
ifconfig_rc=0
wpa_supplicant: wlan0: Failed to initialize driver interface
```

The `-dd` output was going to logcat/syslog, not the wrapper's stdout, so the
real nl80211 error was missing. Image 70r adds:

```text
wpa_supplicant -dd -f /run/wpa.log ...
```

and also captures stderr to `/run/wpa-stderr.log`. The diagnostic report now
includes both files.

## Image identity

- Path: `artifacts/androidgpu70r-ready/wingray-android44-gpu.img`
- Size: 4,427,776 bytes
- SHA-256: `9445b450dbaf6d6c5d9e1ada1d3ff287098c28b6fcb97e3fefa7cca746004407`

## Test

```sh
fastboot flash boot artifacts/androidgpu70r-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70r-report1 \
  --storage-mode android44-readonly
```

The report will show the exact `wpa_supplicant -dd` driver/nl80211 failure.
Image 66 remains the recovery image.
