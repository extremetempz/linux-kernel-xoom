# Power button resolved — Image 78

26 October 2026. **Hardware result:** the real CPCAP back power button works
on Image 78.

```text
Wingray CPCAP VERSC1=0012
CPCAP vendor: ST rev: 2.2 (12)
CPCAP power key initial INTS2=123c
CPCAP power key pressed
CPCAP power key released
```

User confirmation: short press turns the screen off/on; long press opens the
power menu.

Image 78 is the same CS-high/corrected-SPI2 candidate recorded in
[android-power-78.md](../android-power-78.md), SHA-256
`e8a698405f65b9a6b408d66bbf864662bf9830cdc155670d4808474f60dee49d`.

## Fallback retirement

The source tree now restores the volume keys to their normal mapping:

- Volume Up -> `KEY_VOLUMEUP`
- Volume Down -> `KEY_VOLUMEDOWN`
- neither volume key is a wake source

The interim volume-down `KEY_POWER` fallback is removed.

**No rebuild was requested or performed.** The already-flashed Image 78 still
contains the fallback mapping; the source commit removes it for the next
build. The real power button itself is hardware-validated on Image 78.
