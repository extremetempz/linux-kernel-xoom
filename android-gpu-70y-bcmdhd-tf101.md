# Image 70y: wait for Android boot before probing TF101 bcmdhd

25 October 2026. 70x proved the TF101 module was still being loaded at
**2.8 seconds**, even from `on boot`:

```text
dhd_module_init ... @ 173
wl_android_wifictrl_func_add: platform_driver_register timeout
```

The TF101 driver probes SDIO during `module_init` and creates `wlan0` from
that probe. At 2.8 seconds SDIO/card and the display are not settled, so it
created no interface and the early probe disturbed the display.

Image 70y waits inside `/bin/xoom-wifi-load` for
`sys.boot_completed=1`, then loads TF101 bcmdhd 5.90.125.94 once.

## Warning

This is the last TF101 test. If the screen flashes, stop and restore 70t or
Image 66 immediately.

## Image identity

- Path: `artifacts/androidgpu70y-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `61ab58d11b2af7bdc0ed8714a2de01c7584658ab078a5809cbe16bb136fcb4a6`

## Test only if willing

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70y-ready/wingray-android44-gpu.img
fastboot reboot
```

Recovery immediately available:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70t-ready/wingray-android44-gpu.img
```

## Check

- screen stable
- `boot_wait` in `/run/xoom-wifi.log` greater than 0
- `wlan0` exists
- firmware/driver logs and supplicant

If `boot_wait=90`, Android never reported boot complete and the experiment
is inconclusive.
