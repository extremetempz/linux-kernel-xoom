# Image 70f: restore the Xoom OOB host-wake interrupt

25 October 2026. Image 70e fixed WifiHW's fwpath/config/regulatory issues and
reached `SupplicantStartingState`, but the driver open still failed:

```text
dhdsdio_write_vars: Download, Upload and compare of NVRAM succeeded.
dhd_bus_rxctl: resumed on timeout
dhd_bus_devreset: dhd_bus_start fail with -5
dhd_open: failed with code -5
```

The original 2.6 Xoom driver uses an out-of-band host-wake interrupt from
GPIO U5. The 4.4 device tree declares that interrupt on `wifi@1`, but the
legacy driver expects it through the old `wifi_get_irq_number()` board
callback, which was stubbed to `-1`. Without it, the firmware control
channel never completes.

Image 70f:
- restores `OOB_INTR_ONLY`/`HW_OOB`;
- maps the Xoom host-wake GPIO (`TEGRA_GPIO(U, 5)` = 165) to an IRQ,
  active-high, in the legacy driver;
- keeps the 70e fwpath, regulatory, permission and skb-header fixes.

This is the remaining 2.6 board-data difference: the 2.6 driver expects
WL_REG_ON/host-wake GPIO callbacks, while 4.4 describes them in the device
tree. The host-wake callback is now provided; WL_REG_ON is still handled by
the SDIO pwrseq until proven otherwise.

## Image identity

- Path: `artifacts/androidgpu70f-ready/wingray-android44-gpu.img`
- Size: 4,075,520 bytes
- SHA-256: `de255a95a19a48ae2a4565461105907ca00335587380a5606aa006615709d48e`

## Test

```sh
fastboot flash boot artifacts/androidgpu70f-ready/wingray-android44-gpu.img
fastboot reboot
```

Open Settings → Wi-Fi, connect, then capture:

```sh
cd /home/justin/linux-kernel-xoom
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu70f-report1 \
  --storage-mode android44-readonly
```

## Required evidence

1. `dhd_open` completes without `dhd_bus_rxctl` timeout.
2. `wpa_supplicant` starts and scan results appear.
3. Association and DHCP/IP.
4. Display remains stable.

Image 66 remains the recovery image. Power key remains parked; volume-down is
the working wake key.
