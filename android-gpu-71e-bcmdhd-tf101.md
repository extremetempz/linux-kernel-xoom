> **Superseded by Image 72a.** 71e did not change the nl80211 failure.
> 72a switches to the stable 2.6 driver with WEXT. Use
> `android-gpu-72a-wext.md`.

# Image 71e: restore preload and make station SET_INTERFACE a no-op

25 October 2026. 71d removed the preload so WifiHW could own the load. The
log proved WifiHW does **not** load bcmdhd on this ROM:

```text
PROC_NET_WIRELESS: empty
ifconfig: SIOCGIFFLAGS: No such device
nl80211: Set mode ifindex 0
```

So 71d had no module and no `wlan0`; that approach is dead.

71e restores the preload that gave a working driver, `wlan0` and firmware
(at ~43s). The real 71c supplicant error was:

```text
nl80211: Set mode ifindex 3 iftype 2 (STATION)
nl80211: Unsubscribe mgmt frames ... (mode change)
wlan0: Failed to initialize driver interface
```

wpa_supplicant issues `NL80211_CMD_SET_INTERFACE(STATION)` on the existing
primary interface. The 3.1 callback re-runs mode setup and fails. 71e treats
STATION on the existing netdev as a no-op.

## Image identity

- Path: `artifacts/androidgpu71e-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `8329684edcf99721e8afb5074b01762307ed3f972efc96f3b671b2f20bcf8fef`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu71e-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu71e-report1 \
  --storage-mode android44-readonly
```

Check `WPA_LOGCAT` after `nl80211: Set mode`: it should either proceed to
scan/connect or show a different failure. If this still fails, I will stop
patching the driver and change integration approach rather than ask for
another identical test.
