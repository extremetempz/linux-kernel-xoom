> **Update, 23 October 2026:** The isolated plan below was implemented as image 32. Android Welcome responds to touch, and read-only evdev samples verify presses, releases, movement and two active contacts. See [physical result](trace-boot-attempt-32.md). Full edge calibration and suspend remain pending.

# Isolated touch stage after the first Android boot

Source audit, 22 October 2026. Image 31 boots Android to Welcome, but deliberately
does not enable input drivers. This document is a proposed next profile, not a
claim that touch works or that another image has been built/flashed.

Keep image 31 as the known-booting control. Derive a separate touch profile from
the Android/display DT; do not include the entire broad peripheral DTS, which
also enables unvalidated power and peripheral drivers.

Verified against pinned `board-stingray-touch.c`, existing working-ROM captures
and the checked-out Tegra20/mXT drivers:

| Item | Wingray P3 wiring |
|---|---|
| Controller | I2C0 at 0x7000c000, address 0x5b |
| Interrupt | PV2 / GPIO170, low level; P2's PZ2 is not this board |
| Wake/enable | PJ2 / GPIO74, physical low while awake |
| Reset | PR4 / GPIO140, physical low 10ms then high, settle 100ms |
| Supply | Existing shared panel supply; no new blanket PMIC enablement |
| Pin groups | gmd for PJ2, kbcd for PR4, uac for PV2 |
| Known controller | Working ROM reports firmware 0x10FF, family A0, T9 |

The working GPIO capture shows 74 output-low, 140 output-high and 170 input-high.
The actual Tegra20 pin tables confirm the group mapping; retain the tested LCD
and I2C pin mapping and validate all new pull settings against driver support.

Minimum proposed configuration adds `INPUT`, `INPUT_EVDEV`, `INPUT_TOUCHSCREEN`
and `TOUCHSCREEN_ATMEL_MXT`. Keep the Samsung-specific mXT1386 driver disabled.
The existing Wingray mXT branch already handles panel power, active-low wake/reset
and the board timing, skips generic configuration loading, and uses the factory
T9 coordinate range/orientation with direct multi-touch input.

Two concrete source issues should be corrected separately before a touch test:

1. The Wingray branch calls void `mxt_config_cb(NULL, data)`, which discards the
   return from `mxt_configure_objects`. Propagate configuration/input-registration
   errors so a bound driver cannot be mistaken for working input.
2. Generic `update_fw` sysfs remains exposed. Scope firmware/config programming
   interfaces away from this factory-preserving bring-up profile; do not update
   or replace the working controller firmware merely to obtain touch events.

Normal volatile power/calibration operations on input-open are distinct from
NVRAM backup or firmware programming. Review those operations against the
working board before testing; preserve factory configuration.

Hardware acceptance requires correct identity, genuine input registration and
contact/release events, advancing IRQs without a storm, correct edges/orientation
and multi-touch, plus retained USB/display/read-only storage. Creating `/dev/input`
alone addressed the framework assertion; fabricated event nodes and `/dev/uinput`
are not substitutes for this validation.

After real touch is available, finish setup or apply a fixed RAM-only provisioning
step toward the lockscreen. The Welcome UI uses fresh temporary data; current
installed userdata and its saved lockscreen were never mounted by these images.
