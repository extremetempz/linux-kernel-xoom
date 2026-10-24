# Fixed-clock offscreen GPU test 48

Prepared 24 October 2026. **Linux 4.4 GPU rendering is not yet proven.**
This is a testable boot image, rather than another object/link-only checkpoint.
The existing hardware-tested Android, touch, SMP, resource and host profiles
are unchanged. The working Android ROM is the restoration target.

## Evidence and scope

The original 2.6.39 Android ROM rendered two distinct NVIDIA Tegra ES2 frames
with the same probe. Its accepted numeric submission trace shows successful
GR2D and GR3D submissions using the six-word, 24-byte legacy header. The new
profile enables that existing compatibility path and standalone Decatf
semaphore driver. It reuses Decatf's nvhost/nvmap and NVIDIA's existing owner
libraries; it does not implement a replacement GPU driver.

The preceding host test passed three activation/idle cycles at 150 MHz.
Allocator and cached two-client sharing tests passed earlier. None of those
results establishes GPU execution or completion interrupt correctness.

## Separate kernel corrections

| Patch | Change | Offline check |
|---|---|---|
| 0095 / `a3a4235d` | Check reset assertion/deassertion in PMC power-up; unwind clock/power on failure and retain the original error | Actual function compiled with faults at assertion, power, clock, clamp and deassertion; rollback-failure reporting |
| 0096 / `942bc445` | Complete checked reset of an unpublished T20 engine during a balanced active-clock interval; unwind before publication on failure | Actual helper and engine-probe fixtures, including the new fifth failure stage |
| 0097 / `76c80cb2` | Separate Wingray fixed-clock GPU config/DT and software-only EMC votes | Full ARM zImage/DT builds, exact DT-delta validation, actual clock/EMC provider fault fixtures |

The test retains host1x's firmware clock. GR3D is capped at 200 MHz; GR2D/EPP at
100 MHz. Dividers are set before engine clock activation. These are below the
original Motorola source's 950 mV row limits (218.5 MHz GR3D, 133 MHz GR2D/EPP;
`kernel-elementalx-review/arch/arm/mach-tegra/tegra2_dvfs.c`). This source comparison
does **not** verify the device's live rail voltage. No voltage programming or
dynamic frequency scaling is enabled.

The diagnostic requires a CCF-reported boot EMC rate of at least 400 MHz.
Engine-specific software vote clocks accept only votes within that baseline,
check that its reported rate remains unchanged, and never write physical EMC
rates or DRAM timing tables. Only `gr3d`/`gr2d` lookup aliases are registered;
USB keeps its existing clock path. Raw physical-EMC fallback is rejected.
This is an isolated fixed-rate experiment, not operational EMC/DVFS support.

The DT enables only the existing GR2D/GR3D nodes and their Tegra CAR clocks.
It retains the tested Motorola memory reservations and board wiring. Display,
GART, IRAM allocator, AVP/RPC, modern host1x/DRM, suspend and CPU scaling remain
excluded. No Samsung regulators, pinmux, timings or power controls are added.

## RAM runtime and acceptance

The static bootstrap executes the preserved original Android init as PID1,
so bionic receives its normal property workspace. Generated init starts only
ueventd and a one-shot probe service. The original NVIDIA runtime libraries,
shell, linker and probe are copied into the initramfs. `/data` and `/cache`
are tmpfs. No Android block filesystem is mounted; framework, compositor and
display startup are absent. The screen may remain at the Motorola logo.

Only a disposable shell child receives the probe preload. Its own 20-second
alarm and a 35-second outer kill timeout bound ordinary userspace stalls;
a kernel/driver hang may still require the physical reset buttons. USB serves
only framed PING/REPORT requests and captures probe output, clocks, interrupts
and kernel logs. The probe rejects a non-NVIDIA/non-Tegra or software renderer.

Pass requires two fresh reports containing a zero probe exit and
`XOOM_EGL_OFFSCREEN_READBACK_PASS`, with the expected Linux 4.4 GPU-test kernel,
NVIDIA/Tegra ES2 identity and correct distinct frame pixels. Then inspect logs
for faults, completion/timeouts and clock state. This proves only the bounded
offscreen readback workload; it does not validate accelerated Android display,
gralloc/HWC posting, fences, stress, suspend or voltage transitions.

Test sequence: verify both complete live original-image hashes and battery;
flash only boot; collect two fresh reports; return to fastboot; restore original
boot; confirm Android startup and verify both complete original-image hashes.
Never flash recovery or change partition layout.

## Reproduction and artifacts

Build with `XOOM_PROFILE=gpu-test` and a fresh artifact directory using
`scripts/build-wingray.sh`. Package with
`scripts/prepare-gpu-render-diagnostic.py --kernel-dir NEW_KERNEL_DIR --output-dir NEW_IMAGE_DIR`.
Private owner runtime inputs stay under ignored `artifacts/` and are not uploaded.

Accepted local candidate: `artifacts/gpu-render48-v2-ready/wingray-gpu-render-diagnostic.img`,
5,877,760 bytes, SHA256
`5bdf90ce7f02616e3970d26cf5d2f26ee2a598d9741dbb8f86194158a13421f0`.
Kernel/DT/config checks and runtime dependency/header/hash checks pass.
The final compiled mirror matches the edited sources; an initial build using
a toolchain path containing spaces failed and is not accepted build evidence.
Earlier candidate directories are retained, not overwritten.

Hardware outcome belongs in a separate result document after testing.
