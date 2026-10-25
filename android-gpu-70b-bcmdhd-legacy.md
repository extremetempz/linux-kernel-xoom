> **Superseded by Image 70c.** 70b could not load dhd.ko because Linux 4.4
> does not export kernel_thread. Use `android-gpu-70c-bcmdhd-legacy.md`.

# Image 70b: original Xoom bcmdhd, ported to 4.4

25 October 2026. The donor 4.4 bcmdhd reached `wlan0` only through chip-ID
exceptions and was unsafe: 69g produced 131 framebuffer flip failures and a
flashing display. This image uses the original Xoom 2.6.39 bcmdhd driver,
which was written for the BCM4329, `fw_bcmdhd.bin` and `bcm4329.cal`.

## Driver port

- Imported `drivers/net/wireless/bcmdhd-legacy`, built as `dhd.ko`.
- Ported cfg80211 to 4.4:
  - `chandef` for IBSS;
  - `NL80211_STA_INFO_*` station bits;
  - BSS `ies` data/len;
  - 4.4 scan `wdev`, disconnect `locally_generated`, remain-on-channel
    signature;
  - station `scan`, `get_station` and TX-power callbacks;
  - dropped AP/P2P-only cfg80211 ops that are not needed for station mode.
- In-band SDIO interrupts, because the Xoom OOB platform data is not present
  in the 4.4 device tree.
- Module advertises `sdio:c*v02D0d4329*`; vermagic matches
  `4.4.147-wingray-android44-gpu`.

## Runtime

- `xoomwifi` loads `dhd.ko` after `/system` with:
  - `firmware_path=/system/etc/wifi/bcmdhd_sta.bin`
  - `nvram_path=/system/etc/wifi/nvram_net.txt`
- `/system/etc/wifi` overlay supplies both from the ROM's
  `fw_bcmdhd.bin` and `bcm4329.cal`.
- `/system/lib/modules` overlay supplies `dhd.ko`.
- `wlan.driver.status=ok` after a successful load.
- `wpa_supplicant` uses `-Dnl80211`; `dhcpcd` service is defined.
- `xoomawake` and volume-down wake remain.
- `XOOM_WIFI_STATE` diagnostics are included.

## Image identity

- Path: `artifacts/androidgpu70b-ready/wingray-android44-gpu.img`
- Size: 4,075,520 bytes
- SHA-256: `e828af0164d479918409bf00075bb4061ed9800cef65963c19b906a50da04bd4`

## Test

```sh
fastboot flash boot artifacts/androidgpu70b-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect to a network, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70b-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `insmod_rc=0`, `dhd` module present and `wlan0` created.
2. `wpa_supplicant` startup/socket.
3. Scan results and an actual association.
4. DHCP/IP configuration.
5. Display remains stable (the 69g failure must not recur).

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
