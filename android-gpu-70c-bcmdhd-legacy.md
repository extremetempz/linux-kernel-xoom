> **Superseded by Image 70e.** 70c loaded `dhd.ko` and created `wlan0`,
> but WifiHW still lacked the `fwpath` sysfs parameter and a writable
> supplicant config. Use `android-gpu-70e-bcmdhd-legacy.md`.

# Image 70c: fix dhd module load on 4.4

25 October 2026. The 70b report showed the module never loaded:

```text
insmod: can't insert '/lib/modules/dhd.ko': unknown symbol in module
dhd: Unknown symbol kernel_thread (err 0)
```

Linux 4.4 still has `kernel_thread` in the symbol table but no longer
exports it. The original driver's `PROC_START` used it for its watchdog, DPC
and sysioc threads. Image 70c replaces that with exported
`kthread_create`/`wake_up_process` and records `task_pid_nr()` for the
existing stop logic.

All 170 undefined symbols in the resulting `dhd.ko` are exported by this
kernel (`Module.symvers` check); its vermagic matches
`4.4.147-wingray-android44-gpu`.

## Image identity

- Path: `artifacts/androidgpu70c-ready/wingray-android44-gpu.img`
- Size: 4,075,520 bytes
- SHA-256: `1269b90cfe7a1cdc042f8a1840718bfbe2b1d9dbc18697f12bee77dd68590599`

## Test

```sh
fastboot flash boot artifacts/androidgpu70c-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect to a network, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70c-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `insmod_rc=0`, `dhd` module present and `wlan0` created.
2. `wpa_supplicant` startup/socket.
3. Scan results and actual association.
4. DHCP/IP configuration.
5. Display remains stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
