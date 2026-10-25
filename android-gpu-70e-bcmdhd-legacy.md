# Image 70e: close the remaining 2.6 -> 4.4 Wi-Fi integration gaps

25 October 2026. Image 70c loaded `dhd.ko`, created `wlan0`, and loaded the
firmware, but Android Wi-Fi still failed before scanning:

```text
E/WifiHW: Failed to open wlan fw path param (No such file or directory)
E/SoftapController: Softap fwReload failed
E/WifiStateMachine: Failed to reload STA firmware
E/WifiHW: Cannot set RW to "/data/misc/wifi/wpa_supplicant.conf": Operation not permitted
E/WifiStateMachine: Failed to start supplicant!
```

The 2.6 driver also warned at wiphy registration:

```text
wiphy should have REGULATORY_CUSTOM_REG
```

Image 70e fixes the remaining 2.6-to-4.4 boundaries:

1. **fwpath name**: Android WifiHW/SoftapController use the historical
   `/sys/module/dhd/parameters/fwpath`. The legacy driver only exposed
   `firmware_path`; add a `fwpath` alias for the same buffer.
2. **Regulatory API**: set `REGULATORY_CUSTOM_REG` before applying the
   Broadcom regulatory domain.
3. **Supplicant config permissions**: create it owned by `system:wifi`,
   mode `0660`, so WifiHW can read/write it.
4. **skb header representation**: in 4.4 `skb->mac_header` is an offset, not
   a pointer. Pass `skb_mac_header(skb)` to `dhd_wl_host_event()` so scan,
   association and link events are parsed correctly.
5. **Kernel thread API** (already in 70c): use `kthread_create`.

## Image identity

- Path: `artifacts/androidgpu70e-ready/wingray-android44-gpu.img`
- Size: 4,075,520 bytes
- SHA-256: `9d3345533244f8acf346a14f98173f8509f12700b2efa257f82640f01e556a27`

## Test

```sh
fastboot flash boot artifacts/androidgpu70e-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70e-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `insmod_rc=0`, `dhd` loaded, `wlan0` present.
2. WifiHW no longer logs a missing fw path or a config-permission failure.
3. `wpa_supplicant` starts and scan results appear.
4. Actual association and DHCP/IP configuration.
5. Display remains stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
