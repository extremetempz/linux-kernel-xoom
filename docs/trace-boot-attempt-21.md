# Candidate 21: actual USB child probe and connection path

Prepared 20 October 2026 after the user requested log review and redeployment.
Preflight matched both complete original images, Android boot completion,
exact device identity, AC power and 100% battery. The boot-only test is complete;
the original boot image was restored and both complete boot/recovery readbacks
match the preserved originals. Android remains running after trace retrieval.

## Verified source findings versus hypotheses

Build 20 recorded zero from the Tegra PHY probe and Tegra UDC wrapper, plus
a successful scoped userspace mount syscall. This does not prove the child
ChipIdea driver bound: platform-device registration can succeed despite a
child probe failure. The wrapper also ignored the PHY-resume return value.
Both are verified source findings; neither establishes the hardware cause
of missing enumeration.

Patch 0033 propagates a negative PHY-resume result and balances the enabled
clock before returning. Eight cases execute the actual compiled probe with
controlled allocator/OF/clock/child/PHY dependencies; resume failure does
not register a child, and clock/child error cleanup is checked. These are
offline flow checks, not hardware emulation.

Patch 0034 records the actual ChipIdea child probe, serial-gadget bind and
connection snapshots at active-clock driver checkpoints. Tag `ULN1` reuses
the entry-register words inside the existing 128-byte record. Readiness,
header/cookie and first-fatal guards remain; a user-fault record supersedes
USB data. Brief local IRQ masking serializes the UP trace writers, including
the user-fault writer. No forced VBUS/pull-up state, pinmux change or reset
override is introduced.

Thirty-four compiled helper cases check initialized/bounded writes, errors,
first-error/fault preservation, IRQ-state restoration and inaccessible init
memory. Existing diagnostic scratch, user-fault, init-exit, init-exec and
decoder regressions pass. Patch 0035 sets fresh cookie `0x584d0015`.

Image SHA-256:
`2f1d32aa636efba008d2aa59572c8575c3dd70d52bd7e0bd065dcb819a6f5e5c`.
The kernel/DT/config build and measured boot-image audit pass.

## Test scope

Boot only, two-minute USB observation, original boot restoration, full
original boot/recovery readback verification and one unchanged bounded trace
retrieval. Recovery, repartitioning and Android filesystem writes remain
excluded. Raw captures and device identity stay in ignored private artifacts.

## Physical result

One unchanged 128-byte reserved-RAM snapshot has the expected fresh candidate
cookie `0x584d0015` and a valid format-2 header. This candidate had not previously
been tested. It records:

- Actual ChipIdea child probe: returned zero.
- Serial gadget bind: returned zero.
- Connection state `0xf`: VBUS active, OTG capable, gadget driver attached,
  gadget role selected.
- OTGSC `0x08200d00`: B-session valid is set.
- USBCMD `0x00010001`: run/stop is set.
- USBMODE `0x0000000a`: device mode.
- PHY and Tegra wrapper probes, plus a scoped userspace mount, returned zero.
- Init exec succeeded (`0x421`); no first-fatal event or PID 1 fault recorded.

The guest watcher captured zero serial bytes. The candidate ran for more than
two minutes, but the automated USB watcher began about 102 seconds after launch;
it therefore does not establish continuous host observation from initial boot.
The operator returned the device to fastboot. No new screen result was supplied.

These snapshots show successful software setup and a running device controller
at sampled checkpoints. They do not prove a host reset, setup request, valid
PHY clock, electrical data-path connection, interrupt delivery or enumeration.
They also do not establish continuous userspace health or Android running on 4.4.
The earlier missing-VBUS hypothesis is not supported by this snapshot; forcing
VBUS or pull-up bits is not justified.

## Local correction and stop

Subsequent source review found a real error-propagation defect:
`utmi_phy_clk_enable()` logged a failed clock-valid poll but returned no error,
so `utmi_phy_power_on()` and the UDC resume path could still report success.
Patch 0036, donor commit `42413cbe`, returns the poll error and calls the existing
power-off path to balance the pad reference and power down a failed PHY.
It preserves the original startup error if cleanup also times out.

Twenty-four cases compile the actual source functions with controlled MMIO,
poll and pad dependencies. They cover legacy/nonlegacy PHYs, host/peripheral
mode, success and two startup errors, plus cleanup success/failure; they verify
error return, reference balancing, reset/power-down state and skipped post-error
setup. The changed ARM kernel object also compiles. This is not hardware
emulation, and **no clock timeout is proven to have occurred on the Xoom**.
The correction prevents silent success; it is not a confirmed enumeration fix.

The user then requested: “look at the error do a fix but don't do anything else
as i am going to log ooff”. Work stops after this local correction and its
checks. No new boot image, hardware test or GitHub upload was started. The tested
candidate 21 image remains unchanged, and no background watcher remains running.
