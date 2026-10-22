# Image 29: shared LCD pulls and exact backlight rejection evidence

Prepared 22 October 2026; the physical display test subsequently passed. See trace-boot-attempt-29.md for results and full original restoration. Continue the existing port
and the lockscreen objective, using image28's verified USB/storage path.

Source corrections are separate commits/patches:

- `c5368d28` / 0048 moves LCD pulls from the 31 mux-only groups to the six real
  shared pull groups. Data `ld17_0`, `ld19_18`, `ld21_20`, `ld23_22` pull down;
  control `lc`, `ls` pull up. Functions/tristates and timing remain unchanged.
- `6f2c4e9d` / 0049 logs each fixed A1–A7 register and expected production byte
  before returning mismatch status. Negative transfers stop immediately. Chip
  ID mismatch/read errors are explicit. No configuration writes on mismatch;
  no EEPROM writes or relaxed current limits.
- `a8a26819` / 0050 changes only the display trace cookie to `0x584d001d`.

The kernel/profile/DT compile and pass strengthened compiled gates. A source
cross-check against the actual Tegra20 driver validates mux, tristate and pull
capabilities and the legacy shared register fields; it rejects the failed
image28 DT. The actual backlight functions still pass injected read/write
failures, mismatches and all 256 brightness values under UBSan. The framebuffer
and diagnostic scripts/runtime are unchanged from image28; no new Android or
peripheral service is included.

Image SHA-256:
`229b8d412106536995744d6c2e8bc3a955f39c6955a44a4ae247566ea9f6a0d6`.
Release `4.4.147-wingray-display`. Header/load/decompression/DTB audit passes.
The bounded color-bar startup is independent of USB. Reports read the bound
backlight driver's metadata; there is no forced raw access to an owned I2C bus.

Fresh full boot/recovery, identity, power and geometry preflight is required.
Flash boot only under the standing authorization, collect two fresh verified
reports and an operator screen description, restore original boot, then verify
both complete originals after Android returns. No repartitioning, recovery or
Android filesystem write. Do not claim a lockscreen from diagnostic userspace,
a registered framebuffer or a program's draw-complete message.

Acceptance: unsupported pinctrl setting error disappears; capture exact LP8550
values if the guard rejects; if it binds, require fb0 1280×800 and a visible
operator-confirmed pattern with backlight/DRM/clock/IRQ evidence. USB/storage
matching must remain. A backlight mismatch is evidence to investigate against
production source, not permission to overwrite its settings.
