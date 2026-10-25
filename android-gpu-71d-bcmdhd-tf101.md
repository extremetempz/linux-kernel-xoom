> **Superseded by Image 71e.** 71d proved WifiHW does not load the module;
> 71e restores preload and no-ops station SET_INTERFACE. Use
> `android-gpu-71e-bcmdhd-tf101.md`.

# Image 71d: let WifiHW load bcmdhd once

25 October 2026. 71c produced the exact supplicant error:

```text
nl80211: Set mode ifindex 3 iftype 2 (STATION)
nl80211: Unsubscribe mgmt frames ... (mode change)
wlan0: Failed to initialize driver interface
```

and dmesg showed:

```text
Dongle Host Driver @ 42.6   (our preload, firmware up)
Dongle Host Driver @ 62.8   (WifiHW reload; no firmware up)
```

The preloaded module was being unloaded/reloaded by WifiHW when Wi-Fi was
enabled. The second module registered `wlan0`, but its dongle firmware was
not booted, so supplicant's first interface-up failed.

Image 71d removes the preload. `xoom-wifi-load` now only stages the
firmware, NVRAM and module overlays. WifiHW loads bcmdhd exactly once at
Wi-Fi enable; the wrapper brings `wlan0` up, which boots the firmware, and
supplicant initializes against that same module.

The driver also now has default firmware/NVRAM paths compiled in:

```text
/system/vendor/firmware/fw_bcmdhd.bin
/system/etc/wifi/nvram_net.txt
```

so WifiHW's insmod needs no arguments.

## Image identity

- Path: `artifacts/androidgpu71d-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `8d478dd2270ba576448d15e4a0c94d6dba932b13413f599b1eb746c9917d634e`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu71d-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu71d-report1 \
  --storage-mode android44-readonly
```

Expected: one `dhd_module_init`, one firmware-up event, `wlan0` exists, and
`WPA_LOGCAT` should show nl80211 initialization progressing past
`Set mode`.
