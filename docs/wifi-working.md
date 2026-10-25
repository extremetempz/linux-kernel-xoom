# Working Wi-Fi image

Confirmed on hardware, 25 October 2026:

- Wi-Fi scans and lists networks
- WPA2 association and four-way handshake complete
- DHCP obtains an IPv4 address
- disconnect and reconnect both work
- Internet traffic works after reconnecting

## Final image

- Path: `artifacts/androidgpu73k-ready/wingray-android44-gpu.img`
- Size: 4,122,624 bytes
- SHA-256: `8152ad4b5fc7c9bf30760b354bf8f6973c6c82beaeac71874f52aeaf1073f94b`
- Module: native 4.4 `bcmdhd.ko`
- Stripped module SHA-256: `e91291f0a1294ef350d537a3706641a9de328bc7ca5349caa257dd02e9457790`
- Shipped module SHA-256 matches the stripped build module.

## Final route

- Native 4.4 bcmdhd, loaded 40 seconds after boot
- AOSP `fw_bcm4329.bin` (246791 bytes)
- Xoom OEM `bcm4329.cal` NVRAM
- Android's own `wpa_supplicant -Dnl80211`
- `WLC_E_ASSOC` **and** `WLC_E_AUTH` both report the cfg80211 connect result
- Legacy `WLC_SET_SSID` join, 2.4 GHz only, inside the supplicant auth timeout
- `dhcpcd_wlan0` init service defined for `DhcpStateMachine`
- Screen stays stable; `xoomawake` and volume-down wake preserved

## Recovery

- 70t: `artifacts/androidgpu70t-ready/wingray-android44-gpu.img`
- Image 66: `artifacts/androidgpu66-ready/wingray-android44-gpu.img`

## Checks

```sh
python3 tests/test-wingray-wifi.py
```

The exported series in `kernel/patches/` applies cleanly to the pinned
donor and includes the native driver, ASSOC/AUTH connect result, 2.4 GHz
legacy join, and native defconfig.
