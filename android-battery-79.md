# Battery monitor candidate 79 — built, not flashed

26 October 2026. This is the opt-in, monitoring-only battery/charger profile
requested for the Motorola Xoom P3. No device was flashed.

## Step 1 hardware validation

- **BQ20Z75:** source exists in the original tree, but `board-stingray` never
  registers it. It is not the Xoom gauge and was not enabled.
- **Actual gauge:** DS2781 on Tegra OWR/1-Wire. Original board initializes
  `tegra_w1`; the 4.4 tree already has the DS2781 W1 family and power_supply
  core.
- **OWR:** `0x7000c600`, length `0x50`, GIC SPI 30, clock/reset ID 71; OWC
  pinmux OWR pull-up/non-tristate. The opt-in DT matches these.
- **Charger:** BQ24617 on P3 uses PV5/173 STAT1, PD1/25 STAT2 and PV6/174
  DETECT. The monitor requests them as inputs only; no enable or charger
  writes.
- **Android:** healthd consumes standard `battery`/`ac` supplies; battery
  capacity comes from the gauge RARC, not voltage estimation.

The PR's conclusions for step 1 are correct. The main corrections found during
the build were infrastructure, not hardware identification: the battery DTB
was missing from the build/copy list, and a missing monitor caused the
bootstrap to stop Android instead of degrading to a warning.

## Hardware results

- **Test A, disconnected:** 62%, 7.64208 V, -358906 uA, 27.5 C,
  Discharging, ac offline. Android shows the same level and healthd is
  running. See [Test A](docs/battery-79-testA.md).
- **Test B, charger connected:** 61%, Charging, 7.97392 V, +1.529531 A,
  27.7 C, ac online 1. Android reports AC powered, status 2 (charging),
  level 61. See [Test B](docs/battery-79-testB.md).
- **Test C/D:** report3 records four alternating Android `isPlugged`
  false/true transitions without reboot and an extended 432 s connected
  snapshot. Capacity 61–62%, current -358906 → +1531718 uA, no OWR errors or
  crashes. The final snapshot is connected again; an explicit disconnected
  sysfs snapshot is the remaining test-C detail. See
  [Test C/D](docs/battery-79-testC-D.md).

## Image identity

- Path: `artifacts/androidbattery79-ready/wingray-android44-gpu.img`
- Size: 4,145,152 bytes
- SHA-256: `580cb7a243d5274bd455ae520e3af879b53fe98e3db1dc11a467ed1645c9e135`
- Profile: battery monitoring on top of 78/Bluetooth/Wi-Fi/display
- **Not hardware validated**

## Offline checks

All pass:

```text
test-wingray-battery-monitor.py
test-wingray-battery-transport.py
test-wingray-battery-profile.py
test-wingray-cpcap-transport.py
test-wingray-cpcap-key.py
test-wingray-bluetooth-power.py
test-wingray-bluetooth-setup.py
test-wingray-wifi.py
```

The compiled DT has only the battery monitor/OWR nodes on top of the tested
Bluetooth profile; CPCAP bus/CS/pinmux and display configuration are unchanged.
Full ARM kernel, module, battery DT and boot image packing pass.

## Hardware test (later, with explicit approval)

Preserve 78 and recovery first. Flash candidate 79, then run tests A-D from
[docs/battery-monitor-79.md](docs/battery-monitor-79.md): charger disconnected,
connected, disconnected again, and extended monitoring. Capture the battery
report with:

```sh
python3 scripts/capture-framed-diagnostic.py   --output-dir artifacts/androidbattery79-report1   --storage-mode android44-readonly
```

Do not treat compilation or registration as a battery pass. Success requires
real `capacity`, voltage/current/temp where supported, charger transitions and
the Android status bar updating without reboot.
