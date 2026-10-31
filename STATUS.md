> **Image90 prepared (1 November 2026):** full ARM build and offline checks
> pass for a selected CPCAP driver suspend/resume callback transaction after
> task freezing. SPI/IRQs/CPUs stay active; whole-tree device PM and hardware
> sleep remain blocked. No flash, reboot or live test occurred. Known-good89
> is preserved. See [image, scope and procedure](docs/device-pm-90-prepared.md)
> and [LP2 dependency/PMC audit](docs/suspend-lp2-dependencies-90.md).

> **Candidate89 hardware result (28 October 2026):** one task-freezer/thaw
> cycle passed after the requested two-minute wait. Android/USB/storage and
> both CPUs remained healthy; the operator confirmed display/touch/key operation.
> No device/CPU suspend occurred. Candidate89 remains installed and ordinary
> sleep stays blocked. See [hardware evidence](docs/freezer-89-result.md).

> **Candidate89 ready for review (28 October 2026):** a manual task-freezer
> test image is built. It stops before device/CPU suspend and thaws through the
> normal finish path; ordinary sleep stays blocked. The donor null-platform-
> operation bug is corrected separately. Nothing was flashed; candidate88
> remains installed. See [image and test boundaries](docs/freezer-89-prepared.md).

> **Candidate88 hardware result (28 October 2026):** one checked parent
> wake-reference arm/disarm pair passed after the requested two-minute wait.
> Android/USB/storage remained healthy; the operator confirmed power-button,
> full-darkness/display restoration and touch operation. The reference cleared.
> This is awake IRQ/LIC registration, not wake from sleep. Candidate88 remains
> installed; system sleep is blocked. See [evidence](docs/wake-arm-88-result.md).

> **Candidate88 ready for review (28 October 2026):** the combined Android
> image now includes one fixed, manually requested parent wake-arm/disarm test.
> It builds with the Wingray GPU profile retained and PM entry blocked. No new
> image was flashed; candidate85 remains installed. Physical wake and sleep
> remain unvalidated. See [image, checks and procedure](docs/wake-arm-88-prepared.md).

> **DC cycles / wake-arming review (28 October 2026):** ten instrumented
> DC off/on cycles completed; Android/USB/storage remained healthy and the
> operator reported the display looked good. Checked CPCAP parent wake-reference
> code and its isolated profile compile and pass fault tests, but were not flashed
> or tested on hardware. System sleep stays blocked. See
> [DC evidence](docs/dc-hang-85-result.md) and [wake-arm code/build](docs/wake-arm-87.md).

> **Candidate85 hardware result (28 October 2026):** one manually armed
> IRQ/DC off/on cycle passed. The operator confirmed complete darkness,
> restoration without a scan line and working touch. Android/USB/storage
> remained operational; the gate returned to zero. The earlier hang did not
> reproduce; its cause is not established. Suspend remains disabled. See
> [hardware evidence and limits](docs/dc-hang-85-result.md).

> **PM preparation 86 (28 October 2026):** the isolated PM/SUSPEND/hotplug
> framework compiles, but system sleep entry is deliberately blocked. No boot
> image or device test was made. DC recovery, genuine hardware wake and Motorola
> PMC/device restoration remain prerequisites. See
> [preparation and build checks](docs/suspend-preparation-86.md).

# Component status — 28 October 2026

**DC hang candidate 85 — built, not flashed:** A separate manually armed
profile retains candidate84's ECC layout and adds process-context checkpoints
around locks, IRQ shutdown, clock/host transitions and scanout restoration.
It boots with backlight-only blanking; only explicit DCTEST arms one DC cycle.
Full ARM build and targeted offline checks pass. The DC cause remains unknown;
system suspend stays disabled. See [candidate 85](docs/dc-hang-85.md).

**Current suspend baseline — IRQ + backlight hardware pass:** ON IRQ-only,
LIC routing, dynamic virq, polling removal and backlight-only power-key cycles
passed on hardware. Candidate 81 DC worked separately, but the combined
IRQ/DC profile hung and lost USB; the failure is narrowed toward DC, not
root-caused. Suspend/deep sleep remains disabled. See
[hardware result](docs/suspend-wake-82-backlight-result.md).

**Current retained-console gate — two hardware comparisons pass with ECC:**
Candidate 84 booted Android and passed two operator-controlled same-image
warm-reset comparisons. Exact previous markers/379-byte probes survived;
ECC corrected 19 then 25 console bytes, with zero unrecoverable blocks.
Normal reports confirm boot completion and matching read-only storage after
both resets. This is corrected known-probe retention, not error-free RAM or
whole-log/hard-hang/suspend validation. The corruption source remains unknown.
Candidate 84 remains installed; a separate instrumented DC candidate is next.
DC/PM/SUSPEND/DVFS stay disabled. See
[hardware result and remaining gates](docs/suspend-retention-84-result.md).

**Bluetooth — hardware-tested (Image 75b):** The opt-in awake-only
UARTC/rfkill profile paired and connected a Sony WH-1000XM5 headset while
Wi-Fi stayed connected. Setup waits for UART, rfkill, HAL and firmware,
retries after `sys.boot_completed`, and uses rail/reset settling delays.
Full ARM build, power-failure fixtures, setup checks and compiled DT
ownership checks pass. Audio routing, microphone/SCO, suspend/reconnect,
factory address and long coexistence remain unvalidated. See
[Bluetooth working image 75b](android-bluetooth-75.md). The 73k Wi-Fi image
remains the default hardware-tested baseline.

**DC resume candidate 81 — standalone hardware pass; combined regression:**
Native timings and all-window restoration worked on the standalone candidate.
The IRQ/DC combination later hung; do not promote it to the suspend baseline
until retained evidence establishes why. IRQ + backlight-only is the proven
combination. See [candidate 81 result](docs/display-dc-resume-81-result.md) and
[combined failure](docs/suspend-wake-82-hardware-failure.md).

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


**Suspend prep isolation — built, hardware-unverified:** New `wakeirqbl`
profile keeps CPCAP ON IRQ-only (LIC, domain 23, no polling) but removes the
candidate 81 DC resume path, leaving backlight-only display. PM/SUSPEND remain
disabled. Image `7219443f7bfa2caf6be935ecb08162e7c05ef7e3988e5bf385890ecb07317f09`
(4,147,200 bytes) includes fixed read-only PSTORE capture. No hardware test
has been run; Test 5 remains rollback. See
[IRQ + backlight profile](docs/suspend-wake-82-backlight.md).


**IRQ prerequisite — hardware-validated:** The isolated IRQ + backlight-only
image `7219443f…` passed. `wingray_irq_status` reports LIC parent, hwirq 86,
on_virq 115, domain index 23, events 26, errors 0, no unmasked-pending bits;
dmesg shows nested ON press/release events with no polling registration and no
`nobody cared`. Repeated backlight off/on works with `dc=1`. The earlier full
wakeirq failure is narrowed to the DC/candidate-81 path. Pstore is empty
because ramoops reports "no memory-region phandle". Suspend remains disabled
and untested. See
[IRQ result](docs/suspend-wake-82-backlight-result.md).


**Retained console 83 — built, retention unverified:** The opt-in trace
profile adds the ramoops memory-region binding, a guarded read-only pstore
mount and larger bounded PSTORE transfer limits. It keeps IRQ-only CPCAP and
backlight-only display, with DC/PM/SUSPEND off. Offline reservation, framing,
fixture and regression tests pass. Reviewed image:
`9d7e357996403b6ad896d783f10487512e0853575dda73193f4d65ebc59fc329`
(4,149,248 bytes); documented `6e8d2b08…` was not reproduced. Hardware warm-
reset retention is still required. See
[retained-console review](docs/suspend-trace-83-review.md).


**Retained console 83 — ramoops size bug fixed, retention pending:** Hardware
dmesg showed `ramoops: failed to parse property record-size: -75`
(`-EOVERFLOW`) because the trace DT inherited one-cell u32 sizes while this
4.4 driver uses `of_property_read_u64()`. Patch 0155 changes the three trace
sizes to `/bits/ 64`; the compiled DT now has two-cell 64-bit values. The
corrected image `42a2699c9f380a7fce50d2b3348780a9a588a9b3e28a23025168350c4186edfd`
(4,149,248 bytes) builds and passes offline tests. Warm-reset retention is
still pending. See [trace review](docs/suspend-trace-83-review.md).


**Retained console 83 — ramoops binds on hardware:** The fixed trace image
reports `RAMOOPS_BOUND`, read-only pstore mounted, and the intended
0x1ff00000/1 MiB layout with 128K records, 512K console and 128K pmsg. First
boot UUID is 5a938e4d-83e4-4bdb-a8c5-1370ef46fa72; pstore is empty initially,
as expected. Warm-reset retention is still pending. Do not enable DC or
suspend until the previous-boot marker is recovered.


**Retained console 83 — retention partial, one corrupted marker byte:** A
warm reset preserved `console-ramoops-0` (78,329 bytes) and the boot ID
changed from `5a938e4d-…` to `64f4ed82-…`. The old marker was retained as
`5a9s8e4d-…`; `s` is not valid UUID hex, so the record is not bit-exact.
Ramoops binding/mount are correct, but strict retention validation fails until
a second warm reset shows whether this byte corruption is reproducible. Do not
enable DC or suspend.


**Capture validator fixed for retained pstore:** normal trace captures now
accept the fixed `/system/etc/wifi`, `/system/vendor/firmware`,
`/system/lib/modules` RAM overlays and require `/sys/fs/pstore` to be a
read-only pstore mount. The previously failed report re-validates as
`geometry_matches_reference`. The report still shows boot ID `64f4ed82…`,
unchanged from the prior capture, so it does not provide a second warm-reset
retention sample.


**Image 89 — task freezer pass, sleep intentionally blocked:** The manual
freezer test validates preparation/notifier/freezer/thaw and returns to the
same Android session, but `device_suspend=0`, `cpu_sleep=0` and
`ordinary_sleep=blocked`. `MOTOROLA_WINGRAY_PM_PREPARE` makes `pm_suspend()`
return `-EOPNOTSUPP`; `tegra_init_suspend()` never registers platform ops;
PMC parameters, DC/GPU restore, peripheral callbacks and real wake arming are
not validated. No hardware image-89 or ECC retention artifacts are present in
this workspace for independent reproduction. Do not attempt deep sleep. See
[image 89 review](docs/suspend-image89-review.md).


**Image 91 — full-tree devices-only DPM prepared, not flashed:** Adds a
default-off `MOTOROLA_WINGRAY_DPM_TEST` manual profile that reuses Linux
`pm_test=devices` ordering to suspend/resume the whole device tree after task
freeze, with platform/CPU/syscore entry still blocked. CPCAP has separate
selected-test and genuine-DPM callback guards. LP2 source fixes add
`cpu_suspend()` return propagation, one-CPU validation, PL310 outer-cache
disable, timer syscore restore and mode-specific PMC parsing. Display/GPU
system restoration remains blocked. Image size/SHA and the absence of hardware
testing are recorded in [device-pm-91.md](docs/device-pm-91.md). Image 90
review/test procedure is in [device-pm-90-test.md](docs/device-pm-90-test.md).


**Image 91 build identity:** `artifacts/dpm91-final-ready/wingray-android44-gpu.img`,
4,216,832 bytes, SHA-256
`075441429bad1cf5c3d844dfef4d3d4cf6898e1b0865f2cde0cca28e88c2f565`,
profile `android44-devicepm91`. Full-tree devices-only DPM and the LP2 source
corrections build; no device operation or hardware sleep test was performed.


**Image 91 first DPM hardware result — WiFi SDIO EINVAL fixed:** The first
run reached full devices-only DPM, then `mmc1:0001:2` failed with
`-EINVAL` because BCM4329 function 2 requires `MMC_PM_KEEP_POWER` and the
host did not advertise it. The final overlay now sets
`keep-power-in-suspend`; corrected image SHA-256 is
`075441429bad1cf5c3d844dfef4d3d4cf6898e1b0865f2cde0cca28e88c2f565`.
A new hardware run is required; display/GPU restoration remains unresolved.


**Image 91 DPM callbacks pass; DC resume fix pending re-test:** The corrected
WiFi image completed full devices-only `dpm_suspend`/`dpm_resume` with
`WG_PM91_DPM_COMPLETE result=0`; platform/CPU/syscore entry stayed blocked.
USB was lost during the window, so the host frame failed and the result was
recovered from the same-boot dmesg. The panel stayed blank about 30 seconds
because legacy DC resume did not restore the window enable set; the new build
saves window flags and synchronizes a first frame after resume. Corrected image
SHA-256 `075441429bad1cf5c3d844dfef4d3d4cf6898e1b0865f2cde0cca28e88c2f565`.
A second run of the DC-fix image again completed device PM with `result=0`;
the operator observed about five seconds of blanking rather than 30 seconds,
and no scanout-restore failure was logged. Final visual/touch/radio confirmation
is still requested. This remains devices-only PM, not LP2 or deep sleep.


**Image 91 devices-only DPM hardware pass:** Same-boot dmesg records
`WG_PM91_DPM_COMPLETE result=0` at boot `47bd83d8…`; all device
suspend/resume callbacks completed, no scanout-restore failure was logged, and
the operator saw about five seconds of blanking instead of 30. Host USB was
lost during the suspension window, so the framed host response is not proof;
the result comes from the normal report. This is not CPU sleep or LP2. See
[device-pm-91-result.md](docs/device-pm-91-result.md).


**Image 92 suspend-prerequisite diagnostics prepared:** Adds DPM reconnect/
boot-ID status recovery, a fixed CPU1 offline/online diagnostic, and late/
syscore PM test entry points while platform/LP2 entry remains blocked.
Image SHA-256
`55f4165541fdc724b0f15e6d444a0686efc95091045cbfb6cc84720083de51b7`
(4,220,928 bytes). CPU1, late/noirq and syscore are not hardware-validated.
PMC/wake review leaves Image 93 blocked. See
[Image 92](docs/device-pm-92.md) and [PMC/wake review](docs/pmc-wake-92-review.md).


**Image 92 CPU1 hotplug hardware pass:** `CPU1TEST_ONLINE_BEFORE 0-1`,
`CPU1TEST_CPU1_OFFLINE`, `CPU1TEST_ONLINE_AFTER 0-1`, `CPU1TEST_PASS`,
process RC0 on image `e04cb835…`. CPU1 was offlined and returned using the
standard hotplug interface; CPU0 stayed online. This did not combine hotplug
with DPM/LP2. See [cpu1-92-result.md](docs/cpu1-92-result.md).


**Image 92b — late/syscore fixed-request wrappers:** The CPU1-tested kernel now
has fixed `LATETEST`/`SYSCTEST` and `LATESTATUS`/`SYSSTATUS` requests plus
`run-stage-test.py`. Current image SHA-256
`55f4165541fdc724b0f15e6d444a0686efc95091045cbfb6cc84720083de51b7`
(4,218,880 bytes). CPU1 remains hardware-passed on the earlier e04 image with
the same kernel logic; late/noirq and syscore are not yet hardware-tested.
Image 93 remains blocked by PMC/wake and late/syscore gates.


**Image 92 syscore test correction:** The earlier SYSCTEST result0 used
`PM_SUSPEND_FREEZE`; this kernel returns from that path at `freeze_enter()`
before syscore, so it was not a syscore pass. Image 92c now uses a test-only
dummy suspend_ops with `PM_SUSPEND_MEM`/`TEST_CORE`, which reaches
`syscore_suspend()` and stops before the dummy platform enter. Earlier
late/noirq `LATETEST_PASS` remains valid. The corrected syscore path is not
hardware-tested. Image 93 remains blocked.


**Image 92c corrected syscore status pass:** `PM_SUSPEND_MEM` with
`TEST_CORE` reported `SYSCTEST_AFTER completed=1 last_result=0`, counter +1,
process RC0 on image
`55f4165541fdc724b0f15e6d444a0686efc95091045cbfb6cc84720083de51b7`.
This path reaches syscore and skips the dummy platform enter; it is not LP2.
CPU1, late/noirq and syscore diagnostics have passed individually. The PMC
handshake and physical wake remain blocking, so Image 93 is still not prepared.
