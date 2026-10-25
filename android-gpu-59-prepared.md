# Combined accelerated Android candidate 59

25 October 2026. Prepared after [attempt 58's successful physical NVIDIA GPU rendering](gpu-render-test-58-result.md). The user requires the next test boot to target Android with GPU rendering, display/touch, two CPUs, PL310, USB and full-capacity BigPart storage. No intervening offscreen-only test is planned.

## Separate kernel patches

- **0109 / `adb51983`**: permit the fixed-clock GPU experiment with the explicitly selected Wingray legacy framebuffer; add a separate software-only DC EMC vote; retain the original panel's reference-to-sync values in the donor parser; require its existing shared panel regulator and propagate activation/defer failures. It does not change DRAM timing or import Samsung power data.
- **0110 / `499f9226`**: add `wingray_android44_gpu_defconfig`, the combined P3 device tree and fresh trace cookie `0x584d0059`. All previous tested profiles and artifacts remain intact.

The combined DT includes the successful GPU-test resource profile, which already inherits tested SMP/touch/USB/MMC/BigPart wiring. The one ownership change is DC0: Decatf legacy DC/framebuffer replaces modern DRM. It uses the original Motorola 1280x800 AUO timing (66.4 MHz, horizontal 45/26/12, vertical 3/6/3, reference-to-sync 11/1), the tested 598 MHz PLL_C parent and the existing panel rail. The framebuffer occupies the first 8 MiB at `0x2e800000`, inside the existing 24 MiB display reservation and outside the nvmap heap starting at `0x30000000`. There is one display owner. HDMI, Samsung CMC623, GART, modern MC/host1x, DVFS and suspend remain disabled.

The added DC EMC client uses the same bounded software-vote implementation as the tested GPU clients; it cannot set the physical DRAM clock. Tests cover registration/unwind for both two-client GPU-only and three-client GPU+display builds. The legacy rail helper now stops activation if the shared panel rail is missing or fails to enable, and deferred parsing clears its error pointer for the next probe.

## Android integration

The original Android init and existing generated RAM-data service policy are reused. Fixed p8 system is mounted `ro,noload,nosuid,nodev`; data/cache and graphics overlays are tmpfs. No recovery, layout or installed Android filesystem write is packaged.

The RAM overlay selects the installed original `gralloc.tegra.so`, `hwcomposer.tegra.so`, `libEGL_tegra.so`, `libGLESv1_CM_tegra.so` and `libGLESv2_tegra.so`, checked against read-only original-ROM hashes. No software EGL fallback is included in that overlay. The original channels' permissions (0666 root/root) are reproduced only for nvhost-ctrl/gr2d/gr3d, allowing Android clients rather than only the root diagnostic. Other original ueventd policy is retained.

Static non-NEON ABI, CPU-affinity/memory and touch helpers are rebuilt for the new release/config. The framebuffer checker has a separately selected legacy variant requiring the exact Motorola reservation and reported pixel clock; the old software-display behavior remains unchanged. The Android report adds a bounded read-only SurfaceFlinger dump so a Welcome screen cannot be mistaken for GPU rendering proof.

## Offline evidence

- Full ARM zImage/appended-DTB link passes with the combined configuration.
- Compiled-DT comparison preserves all GPU/touch/pinmux/rail/USB/MMC properties outside the intended display change, resolving only schema-defined phandles and preserving IRQ/GPIO arguments.
- Actual fixed-EMC callbacks/registration pass both two- and three-client fault/rollback fixtures without DRAM setters.
- Actual legacy panel-rail failure/duplicate-enable checks pass.
- Existing framebuffer posting/completion/pin-lifetime/timeout fixtures pass; these use host provider mocks, not hardware scanout.
- Original display bounds/draw tests and the new strict legacy-layout checks pass.
- Built-in archive bytes and size match their actual ELF section, and the zImage contains the actual compressed Image. Conservative boot footprint is 11,455,900 bytes, below 16 MiB.
- Actual ARM reset/retained-trace guard checks pass for the fresh cookie. The guarded readback tool recognizes the combined profile and keeps its original-ROM/hash/one-mapping checks.

Image: `artifacts/androidgpu59-ready/wingray-android44-gpu.img`, 3,635,200 bytes, SHA-256 `a4bcfcec93a8ab03823b88fab87120a6f431937f6e77abc16e75151105f2bbda`.

Reproduce into new directories:

```sh
XOOM_BUILD_ROOT=/tmp/xoom-android-gpu-new \
XOOM_ARTIFACT_DIR="$PWD/artifacts/android-gpu-new" \
XOOM_IMAGE_DIR="$PWD/artifacts/android-gpu-new-ready" \
bash scripts/build-android-gpu.sh
```

Local original-ROM references/runtime inputs are required and remain private; the repository does not redistribute proprietary libraries or boot images.

## Hardware verdict still pending

This is the first combined candidate, not a proven accelerated Android boot. The initial compatibility path supports synchronous unscaled linear packed RGB only; tiled/YUV/scaled requests fail explicitly. Actual NVIDIA window-buffer layout, DC completion and HWC behavior must be observed. Do not reinterpret those failures as a need to import Samsung board controls.

The next boot-only test must capture a fresh Android report, renderer/compositor identity, boot completion, CPU probe, touch alignment/multicontact and continued USB/storage operation. Require NVIDIA renderer evidence rather than boot animation/Welcome alone. Restore and completely verify both originals after the test; use the new attempt's guarded retained read only if needed. Attempt 58 proves bounded offscreen GPU rendering, not these combined properties. Wi-Fi, Bluetooth, charging control and DVFS are not added or newly validated.
