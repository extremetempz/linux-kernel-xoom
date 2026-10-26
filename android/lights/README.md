# KitKat Wingray display-power adapter

Opt-in display80 only. Reproduces the Android 4.4.4 ARM32 Lights HAL layout
from AOSP hardware/libhardware include/hardware/{hardware,lights}.h
(Apache-2.0); compile-time checks enforce module/device/state sizes. Source
reference: https://android.googlesource.com/platform/hardware/libhardware/+/android-4.4.4_r2/include/hardware/

All eight KitKat light IDs are opened. Only LIGHT_ID_BACKLIGHT touches
hardware: framework brightness zero writes the fixed backlight sysfs node,
then blanks fixed fb0; the next nonzero request unblanks fb0 before restoring
brightness. The keyboard/buttons/battery/notifications/attention/Bluetooth/
Wi-Fi IDs are accepted as no-ops because KitKat opens every slot and later
calls set_light without a NULL check. Unknown IDs still return ENOSYS.
Nonzero dimming changes do not repost the display; LightsService serializes its
backlight object. No notification/battery LED, charger GPIO, GPU-channel, rail
or SoC suspend control is provided. IO errors on the backlight path are
propagated.

Standalone build uses ARM EABI Linux syscalls and no libc/NDK dependency. The
Android.mk also permits a normal Android module build. Original proprietary
NVIDIA EGL/gralloc/HWC remain unchanged in the existing RAM overlay. This
adapter is locally built open source, not a modified proprietary lights blob.

The old ROM lights.stingray.so is deliberately not copied: it names the LED
class path and unrelated notification/charge-LED controls. The new kernel uses
backlight class. Stage80 init grants system ownership of only brightness.
No existing system partition file is overwritten.

Tests execute the actual C callbacks with faulted file/syscall providers and
verify the compiled ARM ABI. Hardware loading, blank/unblank and physical
brightness still require the separate manual test protocol.
