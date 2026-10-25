> **Superseded by Image 70q.** 70p predates the AOSP BCM4329 firmware
> match from postmarketOS. Use `android-gpu-70q-bcmdhd-legacy.md`.

# Image 70p: bring wlan0 up and record wpa_supplicant's real error

25 October 2026. Image 70o revealed that this Android 4.4 init does not
support the `capabilities` service option:

```text
init: /init.xoom-wifi.rc: 15: invalid option 'capabilities'
```

It also showed that Android brings `wlan0` down after the firmware reload,
then supplicant starts and fails:

```text
Softap fwReload - Ok
CommandListener: Trying to bring down wlan0
wpa_supplicant: Successfully initialized wpa_supplicant
wpa_supplicant: wlan0: Failed to initialize driver interface
```

Image 70p replaces the direct service with `/bin/xoom-wpa`:

- removes the unsupported `capabilities` directive;
- explicitly runs `ifconfig wlan0 up` before supplicant;
- redirects `wpa_supplicant -dd` output to `/run/wpa.log`;
- includes `/run/wpa.log` and the `bcmdhd` sysfs parameters in the report.

The driver remains the `bcmdhd` module with ROM 4.218 firmware, OOB GPIO 165,
WL_REG_ON GPIO 162, preinit tolerance and the vendor firmware path.

## Image identity

- Path: `artifacts/androidgpu70p-ready/wingray-android44-gpu.img`
- Size: 4,077,568 bytes
- SHA-256: `7bed025709f8010d6700005bfdb2ffd90cefde919f7c13c8841854e26558a4bf`

## Test

```sh
fastboot flash boot artifacts/androidgpu70p-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70p-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `ifconfig_rc=0` and `wlan0` up in `/run/wpa.log`.
2. The exact `wpa_supplicant -dd` failure (or successful driver init).
3. No invalid init option.
4. Scan/association/DHCP if driver init succeeds.
5. Display stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
