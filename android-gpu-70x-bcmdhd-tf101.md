# Image 70x: load TF101 bcmdhd after boot, when SDIO is present

25 October 2026. Image 70v loaded the TF101 5.90.125 module at
`on post-fs-data`, around 2.8 seconds. The TF101 driver creates `wlan0`
only when the SDIO function probes, so at that point it registered the
module but never created a net device:

```text
wl_android_wifictrl_func_add: platform_driver_register timeout
initcall dhd_module_init ... returned 0
ifconfig: SIOCGIFFLAGS: No such device
```

The 2.6 driver created `wlan0` unconditionally at module init, which is why
this never appeared before.

Image 70x starts `xoomwifi` from `on boot` instead of `on post-fs-data`.
The SDIO host, regulators and card are up by then, so the module's SDIO probe
can create `wlan0` before Android enables Wi-Fi.

Everything else is unchanged:

- TF101 bcmdhd 5.90.125.94
- AOSP `fw_bcm4329.bin` (246791)
- postmarketOS `nvram_4329.txt`
- WL_REG_ON GPIO 162, OOB GPIO 165
- `xoom-wpa` and DHCP services

## Image identity

- Path: `artifacts/androidgpu70x-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `eacdcf4113c16882162927286911113ecb1509e7c4384425a2d4b05b484078e0`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70x-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70x-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `insmod_rc=0` and `wlan0` exists in `XOOM_NET`
2. `ifconfig_rc=0`, driver firmware 5.90.125.94 / 4.218.248.44
3. `/run/wpa.log` driver init and scan
4. Association and DHCP/IP
5. Display stable

Image 66 remains the recovery image.
