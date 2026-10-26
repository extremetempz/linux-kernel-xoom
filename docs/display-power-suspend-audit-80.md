# Wingray display power and suspend audit — stage 80

26 October 2026. Baseline main `c887905`. No live device access, reboot,
flash, suspend command, regulator change or charging-control change occurred.
Stage 80 implements an **opt-in display blank/unblank experiment**. It does
not claim an extinguished backlight or working suspend without physical tests.

## Original versus donor architecture

Original: Schischu/android_kernel_moto_wingray `jb-mr2`, pinned
`6b3d70fff905b7395fd15992c3779b27d1b6c101`.
Donor: Decatf/linux `android-4.4-p4wifi`, resolves to the existing pinned
`bbcece6d21c83b6280061a91d27566aff1951c94`. This is the donor already in use;
no new Samsung kernel/board import was performed.

Relevant original files: board-stingray.c, board-stingray-panel.c,
board-stingray-power.c, pm.c, wakeups-t2.c. Relevant donor/current files:
arch/arm/mach-tegra/{pm.c,pm-tegra20.c,sleep-tegra20.S,platsmp.c,hotplug.c},
drivers/soc/tegra/pmc.c, drivers/irqchip/irq-tegra.c, legacy tegra video DC/fb,
lp855x_bl.c, CPCAP MFD, bcmdhd, maXTouch and the monitoring/BT drivers.

| Mechanism | Evidence and current limit |
|---|---|
| Original board mode | board-stingray.c selects LP0, CPU good timer 1500, off timer 1, core timer 0x7e7e, core-off 0xf, COREREQ and SYSCLKREQ active-high. These establish original software intent, not physical validation of this port. Core timer values are packed raw register fields: do not copy them into DT microsecond properties without decoding. |
| Original warmboot | The saved P3 original command line contains an 8192-byte lp0_vec at 0x1e7f1020. That blob's availability, reserved-memory ownership and ABI are not established for the new kernel. Its existence is not permission to reuse the address. |
| LP2 | Donor CPU-complex context/flow-controller/CPU suspend path exists. CPU voltage is removed according to PMC requests; DRAM remains active. Candidate for the first later SoC test only after power handshake, CPU hotplug and IRQ wake are proven. Not enabled here. |
| LP1 | Donor copies self-refresh/reset code into IRAM, saves/restores the overwritten IRAM area, stalls memory requests, enters SDRAM self-refresh, and restores CPU clocks/flow control. Installed DRAM/pads, IRAM reservations and resume remain unvalidated on Wingray. |
| LP0 | Original supports it with warmboot and wake routing. Current pm.c explicitly limits accepted platform modes to LP1 or shallower, and PMC entry has LP1/LP2 cases. Do not enable LP0 by changing DT alone. |
| PMC configuration | Current Wingray DT does not supply the complete suspend-mode/timing configuration. PMC defaults to NONE; tegra_init_suspend does not register platform suspend ops in that state. Missing parameters must not be guessed from P4wifi. |
| CPU1 | Tested online SMP is distinct from offline/resume. PM_SLEEP_SMP selects HOTPLUG_CPU; tegra hotplug and warm CPU restart paths exist but have not been exercised on this port. |
| PL310 | Working L2 during awake SMP is proven; CPU/cluster PM and architectural cache save/restore ordering still need separate audit/test. No new cache-size/timing settings were imported. |
| Interrupts/timers | Tegra LIC has wake-mask save/restore and GIC/timer infrastructure exists. The CPCAP DT bypasses LIC through the GIC, so an awake IRQ number is not evidence its wake mask reaches LIC/PMC. Restore/resume of timers/IPIs must be checked after a real cycle. |
| Wake sources | Original wakeups-t2.c maps external PMU to PMC wake18, charger DETECT PV6 to wake14, and BT host-wake PU6 to wake7. These are original mappings, not newly validated wake sources. USB wake entries are not interchangeable with those GPIO/PMU sources. |

## Current configuration and hard gates

The tested battery79 config disables PM, PM_SLEEP/SUSPEND and CPU frequency
scaling; HOTPLUG_CPU is off. WAKELOCK is present, but it alone does not create
working SoC suspend. Stage80 retains these choices. `/sys/power/state` must
be observed on a physical test; a future `mem` entry alone would not prove
hardware low-power entry.

The next conservative platform candidate is LP2, followed by LP1 only if LP2
and all device restore gates pass. **No suspend mode is verified in Linux 4.4
on this tablet.** Therefore this deliverable does not include a flashable
suspend-enabled image or pretend that suspend-to-RAM is implemented. Enabling
PM now would violate the requested dependency on validated display and a
hardware wake source.

### CPCAP IRQ storm and genuine wake

The working power key reads INTS2 bit7 every 20 ms. In the current source,
regmap IRQ registration initializes its software mask state, then the polling
setup directly unmasks ON in the hardware mask register without installing a
nested IRQ consumer. regmap_irq_thread filters status against its own mask
buffer. This mismatch is consistent with the unhandled interrupt storm and
parent IRQ disable seen in the saved battery reports. Other asserted PMIC
sources must also be inspected before assigning the whole storm one cause.

A future focused patch must obtain ON from the third (normal INT1–4) IRQ
chip/domain, use managed mask/unmask/ack through the consumer, handle both
button transitions and register a genuine wakeup source. Relative ON is
INT2 bit7 (23 within the normal domain), not private macro domain index 1.
Parent wake enable must return success through verified LIC/PMC routing;
CPCAP register/sense snapshots and IRQ counts must confirm deassertion.
Then verify wake physically before allowing CPU suspend. Do not suppress the
storm by disabling the parent or declaring an existing polling key wake-capable.

Stage80 deliberately leaves validated SPI2/CS-high/native32 transport and all
CPCAP registers/masks unchanged. It is suitable only for awake display tests.

## Illuminated display: established software gaps versus physical cause

**Verified source/artifact facts:**

1. prepare-android-gpu.py overlays /system/lib/hw with a short fixed module
   list. It omits lights.stingray.so, although the saved original ROM contains
   that module. Android cannot use the omitted module through this overlay.
2. The saved original lights module names `/sys/class/leds/lcd-backlight/brightness`.
   The new kernel exposes `/sys/class/backlight/lcd-backlight/brightness`.
   Copying the old module alone would not fix that ABI path. It also references
   a notification LED and charger-LED GPIO168; those controls are out of scope.
3. lp855x_bl_update_status handles BL_CORE_FBBLANK/SUSPENDED but ignores
   props.power and props.fb_blank. A bl_power write can leave a nonzero
   effective brightness. This is corrected only in the opt-in Wingray profile.
4. Legacy tegra_fb_blank uses a Samsung-style bl-vdd regulator helper and a
   five-second delayed DC shutdown. The Wingray DT provides no bl-vdd supply;
   LP8550 is independently owned and powered from the shared panel rail.
5. FB_BLANK_NORMAL only disables display windows, which is not backlight off.
   Backlight-core notifier state is not a substitute for explicit ownership /
   ordering, especially at first blank and across repeated transitions.
6. The runtime still starts an old forced-screen-awake helper. It is omitted
   from the new profile's init imports, but retained for existing profiles.

These are concrete broken/incomplete software paths that explain how an
illuminated black framebuffer can occur. We did not collect an off-state
hardware trace or measure light output, so **the physical cause is not yet
proven**. Stage80 adds owner-driver logs to establish that path during Test A/B.

### New explicit Android → kernel path

KitKat PowerManager/DisplayPowerController requests brightness through
LightsService and display blanking through SurfaceFlinger/HWC. Reviewed AOSP
android-4.4.4_r2 hardware/lights ABI, HWComposer.cpp and libsuspend sources.
The installed binary's complete blank behaviour has not been established;
therefore do not assume an old HWC blank callback powers off this panel.

The opt-in RAM overlay supplies a small ARM32 lights.stingray.so adapter:

- Accept only the backlight light ID; unsupported LEDs return ENOSYS.
- Use only the fixed backlight brightness path and `/dev/graphics/fb0`.
- Convert framework RGB brightness using the conventional weighted sum.
- Zero brightness is written first, then FBIOBLANK(POWERDOWN).
- On the next nonzero request, FBIOBLANK(UNBLANK) completes before brightness
  is restored. Ordinary nonzero brightness changes do not repost the frame.
- Propagate open/write/short-write/ioctl errors. No GPIO, charger LED, regulator,
  SoC suspend, SurfaceFlinger restart, framebuffer drawing or GPU module change.
- Kernel fb blank calls explicitly bound LP8550 first; a failed off request
  leaves DC running and reports an error. Successful off synchronously disables
  DC through the existing Tegra helpers, with delayed disable work cancelled.
- Resume enables the same mode, posts/synchronizes the retained framebuffer,
  then permits backlight unblank. A timeout/failed update keeps the light off
  and disables DC. Positive remaining-jiffy sync results mean success.

LP8550 retains requested brightness when power flags blank it. Effective zero
uses the existing Motorola P3 device-control-off sequence (register 0x01=0x04),
not a guessed gate GPIO. Brightness zero/off is not proof the actual LEDs went
out: Test A is the physical check. If illumination remains, inspect LP8550
register acknowledgement and original PD0 ownership/polarity before changing
hardware wiring. Stage80 does not seize PD0 or cut the PB2 shared panel/touch
rail; the latter remains always-on. Consequently panel rail removal and touch
scanning shutdown are later stages, not hidden side effects of this fix.

## Android sleep compatibility

AOSP KitKat libsuspend tries early-suspend, then autosleep, then wakeup_count.
Legacy /sys/power/wake_lock compatibility and newer PM_WAKELOCKS are not
interchangeable merely because both names contain wakelock. Original installed
libsuspend backend selection and blocker behaviour need a runtime trace after
framework support is built; source existence is not proof of selected backend.
Do not let two autosuspend mechanisms race or replace the Android framework.

For this display-only experiment, automatic SoC suspend stays impossible by
configuration. The explicit fb ioctl bridge lets display on/off work without
requiring the old early-suspend ABI. Removing only the forced-screen-on service
does not enable kernel suspend.

## Device resume prerequisites before a future suspend profile

| Device | Existing code / work still required |
|---|---|
| GPU/DC | Legacy callbacks exist, but cross-engine submissions, fences, frame ownership, scanout and clocks need repeated real resume checks. Stage80 uses awake DC helpers only. |
| LP8550 | Backlight core suspend/resume support exists; power flags and explicit DC binding are now tested offline. Retained supply versus cold reprogramming needs physical validation. |
| maXTouch | Driver has suspend/resume callbacks and volatile deep-sleep control. Shared panel supply stays enabled; scanning/IRQ disable and slot release/recovery need validation before system suspend. |
| BCM4329 Wi-Fi | Native bcmdhd/SDIO PM callbacks exist. KEEP_POWER, firmware state, OOB/host wake and reconnect need Motorola-specific tests, not Samsung wake GPIOs. |
| Bluetooth | Current driver is expressly awake-only: UART, held device-wake and shared rail votes. No validated host-wake IRQ/LPM/restore; preserve Wi-Fi's power vote while adding PM separately. |
| DS2781/OWR | OWR and monitor have no complete system PM callbacks. Stop/synchronize periodic reads, restore controller clock/timings, refresh measurements and reschedule on resume. W1 enumeration freezer support alone is insufficient. |
| BQ24617 | Polling does not run while asleep. Preserve charger hardware controls; decide and validate DETECT wake14 or sample on resume. |
| eMMC | Existing SDHCI PM support is a starting point. Current /data and /cache remain tmpfs and system is ro,noload; a persistent-data rollout would require separate synchronization/integrity tests. |
| USB | Preserve switch/PHY state, prove restore and any desired wake source explicitly. USB/ADB alone is never the wake/recovery plan. |

## Decision gates and next commits

1. Physically pass ten backlight-only and ten Android blank/unblank cycles.
2. Repair CPCAP IRQ ownership and verify physical hardware wake routing while
   retaining a recoverable awake profile; no global IRQ suppression.
3. Build a separate PM debug/framework profile: PM, SUSPEND, PM_DEBUG and
   PM_SLEEP_DEBUG (if available), PM_SLEEP_SMP/HOTPLUG_CPU and an explicit
   Motorola PMC configuration. Validate the actual installed Android blocker
   backend and a single suspend entry mechanism. Do not enable DVFS.
4. Add each device's PM callbacks separately, with fault/rollback tests.
5. Only then prepare an explicitly approved LP2 hardware test, with logs,
   physical power-button wake and battery-current comparison. Verify CPU1,
   L2/timers/GPU/touch/storage/Wi-Fi/BT/monitor restore and pending wake races.
6. After twenty good cycles, extend duration; only then evaluate LP1 and its
   DRAM/IRAM requirements. LP0 stays unsupported/unverified in this port.

This is the reason later deliverables remain gated, not a claim that a black
screen, a configuration symbol or successful compilation means deep sleep.
