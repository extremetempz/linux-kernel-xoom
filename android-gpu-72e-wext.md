> **Superseded by Image 72f.** 72e started scan but still used iscan result
> handlers. Use `android-gpu-72f-wext.md`.

# Image 72e: standard WEXT scan

25 October 2026. 72d turned Wi-Fi on, but scans failed:

```text
ioctl[SIOCSIWSCAN]: Invalid argument
wlan0: Failed to initiate AP scan
wl_iw_iscan_set_scan: Scan from SIOCGIWSCAN not supported
```

The legacy driver was compiled with `-DCSCAN`; that path deliberately
rejects the standard WEXT `SIOCSIWSCAN` request. Removing `-DCSCAN` selects
`wl_iw_set_scan()`/`wl_iw_get_scan()` instead of the iscan rejection.

72e keeps:

- stable 2.6 bcmdhd with WEXT
- custom WEXT-capable wpa_supplicant running as root
- `CONFIG_PACKET=y` and AF_PACKET
- AOSP firmware / PMOS NVRAM
- `wlan0` up before Wi-Fi enable

## Image identity

- Path: `artifacts/androidgpu72e-ready/wingray-android44-gpu.img`
- Size: 4,063,232 bytes
- SHA-256: `81430a43a1c977c489287e6d5c77f91f576f2acea7408f18246c504e099d22c9`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu72e-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu72e-report1 \
  --storage-mode android44-readonly
```

Expected: no `Scan from SIOCGIWSCAN not supported`, and scan results appear.
