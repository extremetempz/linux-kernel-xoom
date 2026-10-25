# Wi-Fi way forward after 69g

## What the hardware proved

- 69d: `dhd.ko` loads, but bcmdhd built with `CONFIG_DTS` never registers
  the SDIO bus because the `android,bcmdhd_wlan` DT node is absent.
- 69e: direct SDIO registration reaches `dhdsdio_probe_attach` and rejects
  chip `0x4329`.
- 69f: accepting `BCM4329_CHIP_ID` passes chip match and downloads
  `fw_bcmdhd.bin`; `dhd_bus_init` reports ready. The 4330-only
  `CUSTOMER_HW4_DEBUG` validator then aborts `dhd_bus_start`.
- 69g: `SUPPORT_MULTIPLE_CHIPS` bypasses that validator. `wlan0` and `p2p0`
  are registered, but `dhd_preinit_ioctls` returns `-23` for multiple
  firmware ioctls and Android logs 131 framebuffer flip failures. The
  display visibly flashes.

The donor 4.4 bcmdhd is a newer driver paired with newer firmware. The Xoom
ROM supplies the 2012-era `fw_bcmdhd.bin` (version 4.218.248.44) and
`bcm4329.cal`. Reaching `wlan0` through chip-ID exceptions does not make the
host/firmware combination valid, and the result is unstable.

## Decision

Do not continue patching the donor 4.4 bcmdhd. Do not flash 69g again.

The correct driver is the **Xoom 2.6.39 bcmdhd**, which was written for this
4329, this firmware and this calibration file. It is available locally at:

`sources/kernel-elementalx-review/drivers/net/wireless/bcmdhd`

## Port plan

1. Add the 2.6 bcmdhd driver as `dhd.ko` in the 4.4 tree, separate from the
   donor driver.
2. Port its cfg80211 interface to Linux 4.4. The known mismatch classes are:
   IBSS channel/chandef, station-info bitfields, scan/BSS inform APIs and
   disconnect/channel-switch signatures.
3. Keep the original firmware and NVRAM paths, module arguments and the
   `dhd` module name that Android WifiHW expects.
4. Reuse the safe parts of the 69d runtime work: `/system/etc/wifi` and
   `/system/lib/modules` RAM overlays, `wlan.driver.status=ok`, supplicant
   and DHCP services.
5. First milestone is **compile-only** plus a static API review. No hardware
   flash until the module builds cleanly and the display-affecting code is
   unchanged.
6. Only then test `wlan0`, supplicant startup and association.

If the cfg80211 port proves too large, the fallback is the 2.6 bcm4329 WEXT
driver. That is not the first choice because Android 4.4 is built around
NL80211 and WifiHW's `dhd` module/status conventions.

## Device state

Image 66 is the stable recovery image and is currently installed. 69g is
unsafe and must not be reused.
