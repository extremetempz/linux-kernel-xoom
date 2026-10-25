# Image 73i: fast 2.4 GHz legacy join

25 October 2026. Image 73g/73h failed before the join path because the
4.218 firmware rejects an explicit connect channel. 73e's no-channel path
did reach association, but scanned all bands and took ~22 seconds, beyond
the supplicant's 10-second auth timeout.

73i combines the working parts:

- ignore the user-supplied connect channel
- issue `WLC_SET_BAND` / `WLC_BAND_2G` before the legacy join
- join with `WLC_SET_SSID`, no explicit chanspec
- report the cfg80211 connect result on `WLC_E_ASSOC`

This keeps association inside the auth timeout without sending the
chanspec the firmware rejects.

## Image identity

- Path: `artifacts/androidgpu73i-ready/wingray-android44-gpu.img`
- Size: 4,120,576 bytes
- SHA-256: `6e97382c1d07eae0214f3c4d7391d55229eed5002bce562724674c22b4161594`

The module in the image matches the stripped build module.

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73i-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud or the hotspot, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73i-report1 \
  --storage-mode android44-readonly
```

Expected: fast association, `CTRL-EVENT-CONNECTED`, 4-way handshake, DHCP.
