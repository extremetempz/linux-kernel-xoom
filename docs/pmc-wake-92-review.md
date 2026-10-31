# Image 92 PMC, wake and LP2 readiness review

1 November 2026. Source review only; no LP2 entry, CPU power-down or hardware
sleep was attempted.

## Register-level comparison

| Item | Original Motorola (documented) | Current Linux 4.4 | LP2 assessment |
|---|---|---|---|
| CPU good timer | 1500 us | `nvidia,cpu-pwr-good-time`, converted with current pclk in `tegra_pmc_enter_suspend_mode()` | Value known; pclk conversion needs hardware confirmation |
| CPU off timer | 1 us | `nvidia,cpu-pwr-off-time`, same conversion | Value known; conversion needs confirmation |
| Core good timer | `0x7e7e` (LP0/LP1 intent) | Parsed for LP1/LP0 only; unused by LP2 | Not required for LP2, not copied blindly |
| Core off timer | `0x0f` | Parsed for LP1/LP0 only; unused by LP2 | Not required for LP2 |
| COREREQ polarity | active-high | `corereq_high` parsed but **not applied** anywhere | **Blocked/unknown for LP2** |
| SYSCLKREQ polarity | active-high | `tegra_pmc_init()` programs polarity and output enable | Source present; board timing/handshake unverified |
| CPU_PWRREQ | enabled/sequenced | `PMC_CNTRL_CPU_PWRREQ_OE` set in init and entry path | Source present; PMIC response unverified |
| CPU strong/weak timers | not part of this LP2 audit | Function absent/unresolved | **Blocked** |
| LP0 vector | original warmboot ABI | parsed only for LP0, currently not used | LP0 remains excluded |
| Combined request / CPU power-good | board-specific | properties parsed but unused | **Unverified** |

The values do not establish a working PMIC handshake by themselves. The
current code never programs the COREREQ polarity/sequence represented by the
original `corereq_high` field, and it has no proof that the CPCAP/CPU rail
responds correctly to the LP2 request outputs.

## Wake path

- Current awake wake reference: CPCAP parent through Tegra LIC, with regmap-irq
  owning the nested ON mask/ACK. This passed while awake only.
- LP2 wake must rely on LIC syscore mask installation and the PMC/LIC wake
  routing, not merely on `enable_irq_wake()`.
- The original external-PMU wake source mapping is historical evidence; it is
  not proof that the current LIC/PMC route wakes from LP2.
- A physical power-button wake from LP2 has not been tested.
- No polling fallback exists; none should be added.

## Cache/timer/CPU1

- `flush_cache_all(); outer_disable()` is now placed before MMU-off in the
  LP2 finish path. CPU1 offline and DMA quiescence are mandatory preconditions.
- The existing assembly still writes PL310 control zero during MMU shutdown;
  this needs an ordering review against the new outer_disable call before any
  LP2 test.
- Timer `USEC_CFG` now has syscore suspend/resume callbacks. Whether TIMERUS
  actually loses state in LP2, and the ordering against clocksource/clockevent
  resume, remains unverified.
- CPU1 offline/online has an Image 92 diagnostic but has not been run.

## Decision

**Image 93 is not prepared and hardware LP2 remains blocked.**

Concrete blockers:

1. CPU1 hotplug not hardware-validated.
2. Late/noirq and syscore stages not hardware-validated.
3. COREREQ/CPU_PWRREQ/SYSCLKREQ handshake and pclk conversion not proven.
4. Physical CPCAP power-button wake from LP2 not proven.
5. PL310 ordering with the final assembly and CPU1/DMA quiescence not proven.
6. Timer restoration across real LP2 not proven.

No voltage, charging, DVFS or LP1/LP0 change was made.
