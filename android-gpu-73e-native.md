# Image 73e: report connect result on WLC_E_ASSOC

25 October 2026. The full handshake log exposed the real blocker:

```text
wlan0: RX EAPOL from 0a:c4:dd:84:3e:47
wlan0: Not associated - Delay processing of received EAPOL frame
    (state=ASSOCIATING bssid=00:00:00:00:00:00)
...
wlan0: Authentication ... timed out.
```

The firmware reports association completion as **`WLC_E_ASSOC` event 7**.
The 4.4 driver only calls `wl_bss_connect_done()` from `WLC_E_LINK`/
`WLC_E_SET_SSID`, so cfg80211 never receives a connect result. The
supplicant stays in `ASSOCIATING`, refuses to process M1, and the AP
retransmits M1 until deauth.

73e calls `wl_bss_connect_done(cfg, ndev, e, data, true)` on a successful
`WLC_E_ASSOC`, so cfg80211 reports the connection and wpa_supplicant enters
`ASSOCIATED` before the 4-way handshake.

## Image identity

- Path: `artifacts/androidgpu73e-ready/wingray-android44-gpu.img`
- Size: 4,200,448 bytes
- SHA-256: `588b3b866dbddf0e37d1bc48e9b5e4b5e77346800a65868e3fa8f072a31c2ab1`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73e-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud or the hotspot, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73e-report1 \
  --storage-mode android44-readonly
```

Expected:

```text
CTRL-EVENT-CONNECTED
WPA: 4-Way Handshake completed successfully
```

then DHCP.
