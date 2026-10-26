# Battery 79 — Test C/D and transition evidence

26 October 2026. Report:
`artifacts/androidbattery79-report3/report-private.txt` (integrity verified).

The final battery snapshot was taken after reconnecting the charger, so it is
the connected state:

```text
ac/online = 1
battery/capacity = 62
battery/status = Charging
battery/voltage_now = 8012960 uV
battery/current_now = 1531718 uA
battery/temp = 282 (28.2 C)
STAT1 = lo, STAT2 = hi, DETECT = hi

Android: AC powered true, status 2 (charging), level 62,
voltage 8012 mV, current 1531718 uA, temperature 282
```

## Test C — disconnect/reconnect transitions

The report logs four alternating framework plug transitions without a reboot:

```text
update battery state; isPlugged? false*
update battery state; isPlugged? true*
update battery state; isPlugged? false*
update battery state; isPlugged? true*
```

That confirms Android observed charger removal and reinsertion dynamically.
The final snapshot is connected again. Test A already contains the full
disconnected sysfs state (online 0, Discharging, negative current). An exact
sysfs snapshot taken during one of the disconnected intervals would make the
B→C transition evidence complete, but no reboot or stale-state problem was
observed.

## Test D — extended monitoring

- Uptime at capture: **432.75 s**
- Capacity moved 62 → 61 → 62 across the A/B/connected cycles.
- Voltage moved 7.64 V (discharging) → 7.97–8.01 V (charging), consistent
  with charging and plausible for the pack.
- Current changed sign from **-358906 uA** to **+1531718 uA** and remained
  positive while connected.
- Temperature stayed 27.5–28.2 C.
- OWR IRQ 58 reached 33,109 without gauge read errors.
- No kernel crash, no OWR/I2C read failure, and no healthd restart.
- The pre-existing CPCAP IRQ 59 storm/disable remains; CPCAP power-key polling
  still works.

## Assessment

Battery percentage, charger presence, charging/discharging status, voltage,
current and temperature are working in Android. The charging icon path is
confirmed by Android `AC powered=true`, status 2 and `isPlugged=true`; a
screenshot/UI assertion is the only missing cosmetic check.

Remaining non-blocking gaps:

- `health` and `technology` sysfs properties are not exported; healthd logs
  fallback warnings.
- `irq 59` CPCAP storm/disable is pre-existing and unrelated to the battery
  monitor.
- No explicit sysfs capture during a disconnected interval of Test C.
