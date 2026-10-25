# Linux 4.4 NVIDIA GPU offscreen rendering passed

25 October 2026. Attempt 58 reused the exact image 57 binary (SHA-256 `ac2267bd05b370bb3866d53cf725605c05999c8c3e5fccdd3d30394139126a5c`). After a verified USB report, the release tool fetched another fresh report and sent the fixed GPU_RUN command once. The device acknowledged ARMED. The child then completed successfully.

Two independently nonce-verified post-probe reports contain:

```text
egl=1.4 vendor=NVIDIA Corporation renderer=NVIDIA Tegra version=OpenGL ES 2.0
frame=0 triangle_and_background_readback=pass
frame=1 triangle_and_background_readback=pass
XOOM_EGL_OFFSCREEN_READBACK_PASS (not composition/fence validation)
XOOM_GPU_RENDER_EXIT 0
XOOM_GPU_RENDER_PASS
XOOM_GPU_RENDER_DONE
```

This is physical evidence of NVIDIA offscreen rendering on Linux 4.4.147, using the retained Decatf nvhost/nvmap implementation, Motorola resource profile, original NVIDIA userspace and Wingray submission compatibility. It is not software-rendered Android evidence or an inference from device-node existence. The probe's shader draws and two different pixel readbacks completed with NVIDIA/Tegra ES2 identity.

The saved IRQ snapshots show host interrupt count advancing from 2 to 17 and syncpoint IRQ 65 receiving 8 interrupts during the child. Both CPUs' local timers and reschedule IPIs advance. The post-probe reports still match full eMMC capacity and all ten BigPart partition extents. The fixed diagnostic clocks remain host 150 MHz, GR3D 200 MHz and GR2D/EPP 100 MHz; physical EMC remains 600 MHz. No CPU/GPU voltage or DRAM timing table was imported or enabled.

Afterward, the original boot image was restored. Complete original boot and recovery hashes match the preserved backups. The single guarded retained snapshot matches cookie `0x584d0057`: userspace stage 5 confirms the child returned; GR2D and GR3D last runtime stage `0x601` is ioctl 1 returned; panic flag 0. Trace SHA-256 is `df43799035aac78f12faf7771bef7147a8c27cbfaa942865caf896a5566546e8`. Its temporary RAM reader was removed and the original Android boot stayed stable through retrieval.

## Limits and next boot requirement

A successful bounded two-frame pbuffer test is not validation of Android window surfaces, gralloc/HWC composition, framebuffer posting, fence ordering, concurrency, endurance, suspend or DVFS. The test intentionally left display/Android startup disabled, so its Motorola logo was expected.

The user now requires the next test boot to target Android with GPU rendering and preserve previously tested display, touch, SMP, PL310, USB and BigPart storage. Do not schedule another offscreen-only boot. Preserve the exact successful rendering image and software-Android baselines. Prepare a separate combined profile, resolve display ownership and the NVIDIA EGL/gralloc/HWC overlay, then run offline build/resource/ABI checks before its boot-only test. Actual accelerated Android success must be established from renderer/compositor evidence, not just a Welcome screen. Wi-Fi, Bluetooth, charging control and DVFS are not newly validated by attempt 58.
