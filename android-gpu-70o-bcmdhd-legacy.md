# Image 70o: grant wpa_supplicant network capabilities and capture debug

25 October 2026. 70m kept the optional preinit failure from failing
`dhd_open`, but `wlan0` still failed before supplicant could initialize:

```text
Softap fwReload - Ok
CommandListener: Trying to bring down wlan0
wpa_supplicant: Successfully initialized wpa_supplicant
wpa_supplicant: wlan0: Failed to initialize driver interface
```

Android's sequence brings `wlan0` down after the firmware reload, then
supplicant is expected to bring it back up.  The 70l log explicitly showed
`Could not set interface wlan0 flags (UP): Operation not permitted`, so this
image grants the supplicant service explicit network capabilities and enables
its debug log:

- `capabilities NET_ADMIN NET_RAW`
- `wpa_supplicant -dd`

The driver already tolerates the optional `-23` preinit iovars, uses OOB
GPIO 165, drives WL_REG_ON GPIO 162, and loads the ROM 4.218 firmware under
the `bcmdhd` module name.

## Image identity

- Path: `artifacts/androidgpu70o-ready/wingray-android44-gpu.img`
- Size: 4,077,568 bytes
- SHA-256: `1319a36677462fa1a2907cb0ce5aad0ccb2ae7691419611677e47937e4e1a81f`

## Test

```sh
fastboot flash boot artifacts/androidgpu70o-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70o-report1 \
  --storage-mode android44-readonly
```

The report should now contain detailed `wpa_supplicant` messages showing
exactly why the driver interface initialization fails, or show it succeeding.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
