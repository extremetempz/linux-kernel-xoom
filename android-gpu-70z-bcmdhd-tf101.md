> **Superseded by Image 71b.** 70z created wlan0 but loaded after the
> supplicant race. Use `android-gpu-71b-bcmdhd-tf101.md`.

# Image 70z: skip the missing Xoom WiFi platform device

25 October 2026. 70y delayed the module until 63 seconds, and the display was
stable, but `wlan0` still did not exist:

```text
dhd_module_init ... @ 1322
wl_android_wifictrl_func_add: platform_driver_register timeout
ifconfig: SIOCGIFFLAGS: No such device
```

The TF101 init sequence is:

```c
if (wl_android_wifictrl_func_add() < 0)
        goto fail_1;
...
dhd_bus_register();   /* creates wlan0 from the SDIO probe */
```

`wl_android_wifictrl_func_add()` waits one second for the TF101
`bcmdhd_wlan` platform device, which the Xoom does not have. It returns
`-EINVAL`, so `dhd_bus_register()` is never reached.

Image 70z removes that dependency: it powers WL_REG_ON GPIO 162 directly
and calls `dhd_bus_register()` normally. The SDIO card is already present
(`mmc1: new SDIO card`), so the probe can create `wlan0`.

## Image identity

- Path: `artifacts/androidgpu70z-ready/wingray-android44-gpu.img`
- Size: 4,225,024 bytes
- SHA-256: `5b4a848e854a15d8193fab238c78ee5af1a24938713b93f6e23dd6bcb46e607e`

## Status

This is the final code change I have. Screen was stable on 70y. I am not
asking for another flash; the image is available if you choose to test it.

Recovery remains 70t or Image 66.

If tested:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70z-ready/wingray-android44-gpu.img
fastboot reboot
```

Check `wlan0` first. If it exists, the SDIO/platform blocker is solved; the
remaining work is supplicant/association.
