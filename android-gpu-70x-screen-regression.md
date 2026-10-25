# Image 70x is unsafe: TF101 driver causes screen flashing

25 October 2026. Image 70x still did not create `wlan0`:

```text
insmod_rc=0
wl_android_wifictrl_func_add: platform_driver_register timeout
ifconfig: SIOCGIFFLAGS: No such device
```

It also caused the display to flash. The TF101 5.90.125 driver is not
viable on this 4.4 Xoom display/kernel combination. Do not flash 70x again.

## Recover

Flash Image 66:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu66-ready/wingray-android44-gpu.img
fastboot reboot
```

- Image 66 size: 3,651,584 bytes
- SHA-256: `37956a4d758f28406bb32d498f993160e27dda16184a2f1b031b6c95e360ef6a`

Image 70t is the stable 2.6-driver baseline:

```sh
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu70t-ready/wingray-android44-gpu.img
```

- Image 70t size: 4,247,552 bytes
- SHA-256: `1524e1f54a50950060ee9398342c0cbbf83f525495f0baafb386b72b8c1c69b7`

The build script is reverted to the legacy 2.6 driver. The TF101 driver port
is abandoned.
