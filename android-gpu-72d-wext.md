> **Superseded by Image 72e.** 72d enabled Wi-Fi but CSCAN rejected WEXT
> scans. Use `android-gpu-72e-wext.md`.

# Image 72d: AF_PACKET and root supplicant

25 October 2026. 72c finally initialized the WEXT driver, but failed at:

```text
l2_packet_init: socket(PF_PACKET): Address family not supported by protocol
WEXT: SIOCSIWAUTH(...): Operation not permitted
Could not set interface wlan0 flags (DOWN): Operation not permitted
```

Two missing foundations:

1. `CONFIG_PACKET` was **not set** in the kernel config, so AF_PACKET
   sockets (needed by wpa_supplicant's EAPOL l2_packet) did not exist.
2. The supplicant dropped from root to uid `wifi` without `CAP_NET_ADMIN`,
   so the WEXT ioctls returned EPERM.

72d:

- enables `CONFIG_PACKET=y`
- builds the supplicant with `ANDROID_NO_DROP_PRIVS` so it keeps root and
  retains CAP_NET_ADMIN/CAP_NET_RAW
- keeps WEXT, the Android control socket and the stable 2.6 driver

## Image identity

- Path: `artifacts/androidgpu72d-ready/wingray-android44-gpu.img`
- Size: 4,061,184 bytes
- SHA-256: `af7257bacad9217aef97686957f0358b4a68c816fedc89e7117aea5bb50b9691`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu72d-ready/wingray-android44-gpu.img
fastboot reboot
```

Turn Wi-Fi on, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu72d-report1 \
  --storage-mode android44-readonly
```

Expected `WPA_LOGCAT`:

- `l2_packet_init` succeeds
- no `Operation not permitted` on `SIOCSIWAUTH`
- WEXT scan starts, then association

Recovery: 70t or Image 66.
