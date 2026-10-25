> **Superseded by Image 73a.** 72f froze on the Wi-Fi screen. The custom
> WEXT path is abandoned; 73a uses the native 4.4 driver. Use
> `android-gpu-73a-native.md`.

# Image 72f: standard WEXT scan handlers

25 October 2026. 72e made `SIOCSIWSCAN` succeed (`ret=0`), but result reads
still failed:

```text
wl_iw_iscan_get_scansysioc_pid
wl_iw_iscan_set_scan error
wlan0: Failed to get scan results
```

The driver still used the iscan handler table. 72f keeps iscan helper code
compiled (for its prototypes and iovar helpers) but wires the standard WEXT
handlers:

```text
SIOCSIWSCAN  -> wl_iw_set_scan   (WLC_SCAN)
SIOCGIWSCAN  -> wl_iw_get_scan   (WLC_SCAN_RESULTS)
```

This is the scan path wpa_supplicant and Settings expect.

## Image identity

- Path: `artifacts/androidgpu72f-ready/wingray-android44-gpu.img`
- Size: 4,061,184 bytes
- SHA-256: `c0b7d8ad2e0eab6bbfd48580c077e96866762cf5bd332242d58dc6406ed4966c`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu72f-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu72f-report1 \
  --storage-mode android44-readonly
```

Expected: `SIOCGIWSCAN` returns results, Settings lists networks.
