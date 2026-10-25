# Image 73k: also report the connect result on AUTH success

25 October 2026. 73j obtained a DHCP lease once, then later reconnects
failed:

```text
wlan0: RX EAPOL from 18:e8:29:4b:5e:6a
wlan0: Not associated - Delay processing ... (state=ASSOCIATING)
wlan0: Authentication ... timed out.
```

The failure log contains only `wl_get_auth_assoc_status : event=3` (auth
success), with M1 frames arriving, but **no `event=7` (WLC_E_ASSOC)**.
wpa_supplicant therefore stays in `ASSOCIATING` and ignores M1.

73k reports the cfg80211 connect result on **both** successful
`WLC_E_ASSOC` and `WLC_E_AUTH`. This makes reconnects follow the same
path as the one successful connection.

## Image identity

- Path: `artifacts/androidgpu73k-ready/wingray-android44-gpu.img`
- Size: 4,122,624 bytes
- SHA-256: `8152ad4b5fc7c9bf30760b354bf8f6973c6c82beaeac71874f52aeaf1073f94b`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73k-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud, disconnect/reconnect once, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73k-report1 \
  --storage-mode android44-readonly
```

Expected: the second association also reaches `CTRL-EVENT-CONNECTED` and
gets a DHCP lease.
