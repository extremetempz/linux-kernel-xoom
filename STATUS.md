# Component status — 26 October 2026

**Suspend preparation 82 — built, not hardware-tested:** A separate `wakeirq`
profile replaces key polling with a managed normal-domain ON IRQ and routes
the same PMU interrupt through Tegra LIC. The tested candidate 81 and Test 5
profiles remain intact. Suspend/deep sleep is still disabled; first validate
awake IRQ delivery and absence of a storm. See [build and staged gates](docs/suspend-wake-82.md).

**Bluetooth — hardware-tested (Image 75b):** The opt-in awake-only
UARTC/rfkill profile paired and connected a Sony WH-1000XM5 headset while
Wi-Fi stayed connected. Setup waits for UART, rfkill, HAL and firmware,
retries after `sys.boot_completed`, and uses rail/reset settling delays.
Full ARM build, power-failure fixtures, setup checks and compiled DT
ownership checks pass. Audio routing, microphone/SCO, suspend/reconnect,
factory address and long coexistence remain unvalidated. See
[Bluetooth working image 75b](android-bluetooth-75.md). The 73k Wi-Fi image
remains the default hardware-tested baseline.

**DC resume candidate 81 — built, hardware-unverified:** Separate opt-in
`displaydc` profile corrects native-mode round-trip loss and restores all
legacy scanout windows under the flip lock. The validated `displaypm` profile
remains backlight-only. No flash, reboot, suspend or regulator changes. See
[analysis and test gates](docs/display-dc-resume-81.md).

**Display power — backlight-only hardware pass:** Image
`display80fbtest5` is hardware-validated. Power off/on extinguishes and
restores the LP8550 backlight with `dc=1`; the panel returns without a line.
The DC power-down experiment reached `dc=0`/`dc=1` but left the panel dark and
is rolled back. All eight light IDs are safely opened. Suspend-to-RAM/deep
sleep and DVFS remain disabled, gated on a proper panel reset/power sequence
and hardware wake validation. See [Test 5](docs/display-power-80-test5-result.md),
[DC rollback](docs/display-power-80-dc-rollback.md),
[candidate 80](android-display-80.md) and
[test protocol](docs/display-power-80-test.md).

**Battery monitor — Tests A/B/C/D pass at framework level:** The opt-in
profile exposes the real P3 DS2781 gauge over Tegra OWR and BQ24617
STAT1/STAT2/DETECT inputs as standard `battery` and `ac` supplies.
Disconnected: 62%, 7.64208 V, -358906 uA, 27.5 C, Discharging, ac offline.
Connected: 61–62%, Charging, 7.97–8.01 V, +1.529–1.532 A, ac online; Android
reports AC powered/status 2. Report3 records four `isPlugged` false/true
transitions without reboot and 432 s of monitoring with no OWR errors or
crashes. Remaining non-blocking gaps: `health`/`technology` sysfs properties,
an explicit disconnected sysfs snapshot during Test C, and the pre-existing
CPCAP IRQ 59 storm (unrelated; power-key polling works). See
[candidate 79](android-battery-79.md), [Test A](docs/battery-79-testA.md),
[Test B](docs/battery-79-testB.md), [Test C/D](docs/battery-79-testC-D.md)
and [monitor protocol](docs/battery-monitor-79.md). No charger/voltage/current
control or calibration writes are enabled.

**Power button — hardware-validated on Image 78:** CPCAP now returns
`VERSC1=0012` / ST rev 2.2. The physical back button emits press/release
events; short press toggles the screen and long press opens the power menu.
The source tree retires the interim volume-down `KEY_POWER` fallback and
restores normal `KEY_VOLUMEDOWN`/`KEY_VOLUMEUP` keys. No rebuild was
performed, so the currently flashed 78 image still has the old fallback
mapping. See [power-button result](docs/power-key-78-result.md),
[77 findings](docs/power-key-77-findings.md) and
[candidate 78](android-power-78.md). 75b and 73k remain stable baselines.

**Latest hardware result — Wi-Fi (Image 73k):** Native 4.4 `bcmdhd` on the
BCM4329 now works for station mode on Android 4.4.4. Image 73k scans 2.4 GHz
networks, completes WPA2 association and the four-way handshake, gets a DHCP
lease, reconnects after disconnect and passes Internet traffic. The route uses
the Xoom OEM NVRAM, Android's native `nl80211` supplicant, the legacy
`WLC_SET_SSID` join on 2.4 GHz, the `WLC_E_ASSOC`/`WLC_E_AUTH` connect result,
and the `dhcpcd_wlan0` init service.

- Image: `artifacts/androidgpu73k-ready/wingray-android44-gpu.img`
- Size: 4,122,624 bytes
- SHA-256: `8152ad4b5fc7c9bf30760b354bf8f6973c6c82beaeac71874f52aeaf1073f94b`
- Recovery: 70t and Image 66
- Limit: 2.4 GHz station mode; 5 GHz, SoftAP and long suspend/resume soak
  testing are not validated.

See [the working Wi-Fi record](docs/wifi-working.md).

**Previous GPU/touch result (Image 63/64):** Android 4.4.4 now displays on the
Xoom through the NVIDIA GPU composition path. The setup wizard, status bar,
navigation bar and wallpaper are visible, the Tegra DC scans out the
GPU-composed 1280x800 framebuffer, and the LP8550 backlight is on. This is
GPU/client-target composition, not HWC overlay composition
(`numHwLayers=0`). Image 64 additionally verifies real touch input: 25 presses,
22 releases, 840 position events, three simultaneous contacts and a maXTouch
IRQ advance from 977 to 1,169. See [Image 63 result](android-gpu-63-result.md)
and [Image 64 touch result](android-gpu-64-touch-result.md). Original
boot/recovery restoration is pending after these tests.

**Latest GPU status:** [attempt 58](docs/gpu-render-test-58-result.md) physically passes NVIDIA Tegra OpenGL ES 2.0 offscreen rendering on Linux 4.4.147: two distinct frames have correct triangle/background readbacks and the child exits 0. Two fresh reports confirm the result. The original boot/recovery hashes match after restoration, and retained checkpoints confirm child completion without a recorded panic. Android accelerated window/compositor integration remains unproven. The next test boot must target combined accelerated Android with the previously tested display, touch, SMP, PL310, USB and storage; no further offscreen-only boot is planned.

**Combined Android test:** image 59 reached USB, matching storage, Android ABI and two-core checks but stopped before Android at a missing framebuffer bus resource. [Image 60](docs/android-gpu-60-framebuffer-map.md) adds only the exact reserved fb0 bus window and a fresh trace cookie; its Android archive is byte-identical. It is flashed and under observation. Original restoration remains pending for this test; recovery/layout remain untouched. Combined accelerated Android is not yet proven.

**Hardware-tested baseline:** Linux 4.4.147 boots the existing Android 4.4.4
userspace. Image 32 displayed Welcome with working touch; image 33 confirms
Android completion, real single/two-contact events, USB, full eMMC capacity and
all ten BigPart extents without the earlier startup IRQ burst. Original boot
and recovery were restored and completely verified. A lockscreen has not been
verified. This is an experimental RAM-data/software-graphics boot, not a complete
ROM or a newer Android release. Images 37/38 additionally confirm initial
two-core Android boots with PL310, with and without diagnostic tracing.

| Component | What is done | What is not done | Verdict |
|---|---|---|---|
| Wi-Fi (BCM4329 / native bcmdhd) | Image 73k physically confirms scan, WPA2 association, four-way handshake, DHCP, disconnect/reconnect and Internet traffic; native 4.4 `bcmdhd`, Xoom OEM NVRAM, `nl80211` supplicant and `dhcpcd_wlan0` | 2.4 GHz station mode only; 5 GHz, SoftAP, roaming and long suspend/resume soak unvalidated | Station-mode Wi-Fi and DHCP confirmed |
| Bluetooth (BCM4329 / native rfkill) | Image 75b pairs/connects a Sony WH-1000XM5; `ttyHS2`, rfkill, HCI traffic, Android Bluetooth service and Wi-Fi coexistence confirmed | A2DP/SCO audio, mic, suspend/reconnect, factory address and long coexistence unvalidated | Pairing and connection confirmed; awake-only profile |
| Tegra 2 SMP / CPU bring-up | Images 37 (traced) and 38 (unchanged non-trace image 36) boot Android with both CPUs online; CPU probes and timer/reschedule-IPI progress pass | Earlier attempt-36 failure remains unexplained; broader repeatability, concurrent stress, hotplug and suspend unvalidated | Initial traced and non-traced two-core boots passed; not fully validated |
| PL310 L2 | Images 34/35/37/38 boot Android with PL310 enabled, 1 MiB; CPU0 and bounded cross-CPU memory checks pass | Broader cache-capacity, RAM-pressure and endurance validation pending | Initial UP/SMP smoke tests passed; not fully validated |
| CPU frequency / voltage | Clock acquisition/unwind, shared EMC failure/rollback reporting, PLL error propagation, voltage-unit correction and stock Wingray table cap implemented; fault tests and ARM object checks pass | Motorola OPP/rail coupling, installed-DRAM EMC tables, voltage-failure veto and complete transition sequencing unvalidated; scaling/voltage driver remain disabled in tested profiles | Prerequisites implemented; not operational |
| NVIDIA nvhost / nvmap | ARM32/submission corrections and reservation checks implemented; separate Motorola carveout-only DT/config builds with matched live-original 256 MiB heap, no IRAM/GART/engines, EMC shims or DVFS; full legacy graphics links also pass; patches 0081–0084 reject clock/IRQ/probe failures and unwind partial setup, with fault tests and full ARM links; attempt 39 boots the isolated profile and passes four 64 KiB uncached create/allocate/pin/map/pattern/cache-ioctl/unmap/unpin/free cycles, with two fresh reports and verified original-image restoration; attempt 40 additionally passes cacheable two-client pattern exchange and imported mapping survival after owner release | DMA coherency, cross-process/concurrent sharing, lifetime stress, host/GART/DC ownership and extended submission/concurrency coverage pending; tested Android profiles retain software graphics | Allocator/sharing and bounded NVIDIA GPU rendering passed; Android graphics integration pending |
| EGL / gralloc / HWC | Software graphics reaches Android Welcome; composer bounds/descriptor cleanup corrected; original framebuffer ABI restored with optional synchronous linear-RGB handlers, bounds/completion/lifetime tests and ARM on/off links; offscreen probe passes 13 host cases and now runs two correct NVIDIA Tegra ES2 frames on both the original 2.6.39 ROM and Linux 4.4.147 in attempt 58 | Tiled/YUV/scaled posting unsupported; matched accelerated Android image/HAL integration, actual posting/completion/concurrency and accelerated composition pending | Initial RGB compatibility implemented offline; accelerated integration incomplete |
| Android 4.4 Binder / ashmem / logger / VM | Real framework startup, Binder protocol 7 check, logger v1/v2 round trips, private-page ashmem test and existing VM/LMK startup demonstrated physically; expanded pin/protection probe passes physically in images 34/35/37/38 | Full Binder transaction/FD, reclaim/OOM and endurance coverage pending; wallpaper RenderScript crashes and Play services ANRs unresolved | Basic KitKat support demonstrated; not fully validated |

Do not count the component headings as independently completed hardware
features. The strongest validated milestone is Android 4.4.4 startup with
display, touch, Wi-Fi, USB and storage. Non-trace SMP repeatability, broader
L2 validation, DVFS and accelerated Android display integration remain
separate work.

## Final Wi-Fi image

[Image 73k](artifacts/androidgpu73k-ready/wingray-android44-gpu.img) is the
confirmed Wi-Fi release: 4,122,624 bytes, SHA-256
`8152ad4b5fc7c9bf30760b354bf8f6973c6c82beaeac71874f52aeaf1073f94b`.
The shipped stripped module matches the build. See
[the working Wi-Fi record](docs/wifi-working.md) and
[the native-driver test](tests/test-wingray-wifi.py).

## Source and evidence

- [Working Wi-Fi record](docs/wifi-working.md)
- [Image 33 physical results](docs/trace-boot-attempt-33.md)
- [Image 34 PL310 results](docs/trace-boot-attempt-34.md)
- [Image 35 SMP control results](docs/trace-boot-attempt-35.md)
- [Image 36 two-CPU observation](docs/trace-boot-attempt-36.md)
- [Image 37 two-core Android hardware results](docs/trace-boot-attempt-37.md)
- [Attempt 38 unchanged non-trace two-core boot](docs/trace-boot-attempt-38.md)
- [Image 37 startup trace and validation limits](docs/smp-startup-trace-37.md)
- [PL310/SMP implementation and build controls](docs/decatf-implementation-progress.md)
- [Power, graphics and Android ABI corrections and next gates](docs/power-graphics-abi-stage.md)
- [Decatf graphics full-link corrections, framebuffer gap and rendering test](docs/decatf-graphics-integration.md)
- [Motorola resource validation and initial RGB framebuffer compatibility](docs/graphics-compatibility-42.md)
- [GPU probe on original ROM, clock correction and remaining Linux 4.4 blockers](docs/gpu-rendering-preparation-41.md)
- [Attempt 40 cached sharing and owner-release hardware results](docs/nvmap-cached-sharing-hardware-test.md)
- [Attempt 39 physical allocator smoke test and limitations](docs/nvmap-allocator-hardware-test.md)
- [Built Motorola carveout-only resource profile and original live heap observations](docs/wingray-legacy-resource-profile.md)
- [Decatf reuse classifications and staged plan](docs/decatf-reuse-plan.md)

Kernel corrections are separate exported commits through the current series
(including the native Wi-Fi patches 0137–0139); Android
wrapper changes are separate patches under `android/patches`. Sources, tests
and sanitized findings are committed; proprietary libraries, original device
images, identifiers and raw hardware reports are excluded. Tested configurations
and boot artifacts are preserved. No Samsung board power or display tables were
imported by these stages.

With Wi-Fi station mode delivered, Bluetooth, charging and the remaining
display/graphics gates are future work. [Channel-publication correction and
remaining gates](docs/graphics-channel-publication-43.md) records patch 0085,
its fault tests and ARM link, and the runtime clock/EMC/submission gaps. Linux
4.4 acceleration remains unproven; no new flash.

[Runtime/submission integration](docs/graphics-runtime-integration-44.md) adds
checked parent, EMC, clock and IRQ activation to the main submission path and
related entry points. Patches 0086/0087 pass fault fixtures and the full ARM link.
Motorola resource/provider validation and Linux 4.4 GPU rendering remain
unproven; no device access or flash occurred in this stage.

[Host-only diagnostic image prepared](docs/host-test-image-45-prepared.md):
a separate boot image now packages the checked host clock/IRQ cycle test,
original allocator layout and USB RAM reporter. Offline gates pass; it has
not been flashed and performs no GPU rendering or Android startup.

[Initial host-only hardware test passed](docs/host-test-image-45-result.md):
one physical boot completed three checked host activation/suspend cycles at
the retained 150 MHz rate, with two fresh USB/storage reports and a final zero
host reference count. The original boot was restored and both complete original
partition hashes verified. This does not establish GPU submission/rendering or
completion interrupt delivery; an inherited fsync permission warning remains.

[GPU submission/semaphore checkpoint](docs/gpu-submission-semaphore-46.md):
the isolated original-ROM EGL trace confirms 24-byte headers and use of both
GR2D/GR3D. Decatf semaphore reuse without RPC/AVP and engine-host deferral are
separate patches 0091/0092; fixtures and the full ARM link pass. No new flash or
Linux 4.4 GPU rendering result. Work stopped at the requested usage checkpoint.

[GPU client lifetime checkpoint](docs/gpu-client-lifetime-47.md): patches
0093/0094 reject failed GR3D context-save pins, release partial handlers and
publish engine channels after module initialization. Actual-function fault
fixtures and a fresh full ARM graphics link pass with the prior compile config
unchanged. Checked pre-publication reset and Motorola EMC integration remain;
no new boot image, flash or Linux 4.4 GPU rendering result.


**Display DC resume — candidate 81 hardware-validated:** The reviewed
candidate 81 image (`e02c7c41…`, 4,147,200 bytes) was flashed and display
power off/on now works with no scan line. It retains native mode, restores all
scanout windows and serializes flips. Test 5 (`02ab70c2…`) remains the
known-good backlight-only rollback. Suspend, automatic suspend, LP1/LP0 and
DVFS remain disabled and untested. See
[candidate 81 result](docs/display-dc-resume-81-result.md).


**Suspend prep 82 — awake IRQ profile built, hardware-unverified:** CPCAP ON
is registered through the normal regmap nested domain (domain index 23),
routed through Tegra LIC, with the 20 ms polling worker absent. The profile
keeps candidate 81 display code and PM/SUSPEND disabled. Offline handler,
DT/config and regression tests pass; the reviewed image is
`f6ab7071972890c6789aafa501653230739f6f5ae60c8e79a48fa7f8740ec3cb`
(4,149,248 bytes). The PR's documented `c0a7f7b6…` was not reproduced. No
hardware IRQ or wake test has been run. See
[suspend-prep review](docs/suspend-wake-82-review.md).


**Suspend prep 82 — awake IRQ test FAILED:** The wakeirq image initially
behaved, but turning the screen off made the tablet unable to wake and the
USB gadget disappeared; a reboot recovered it, and a second attempt failed
again. No log could be captured. This is not deep sleep (PM/SUSPEND are
disabled in that profile); either the new LIC/regmap ON path or the inherited
candidate 81 DC resume is implicated. Do not reflash wakeirq and do not
attempt suspend. Restore Test 5 backlight-only. See
[suspend-prep failure](docs/suspend-wake-82-hardware-failure.md).
