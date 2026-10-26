# Battery 79 — Test B result

26 October 2026. Charger connected. Report:
`artifacts/androidbattery79-report2/report-private.txt` (integrity verified).

## Kernel power_supply

```text
ac:
  type = Mains
  online = 1

battery:
  capacity = 61
  status = Charging
  voltage_now = 7973920 uV   (7.97392 V)
  current_now = 1529531 uA   (+1.529531 A)
  temp = 277                 (27.7 C)
```

Charger GPIOs:

```text
gpio-25  wingray-stat2   in hi
gpio-173 wingray-stat1   in lo   (charging)
gpio-174 wingray-detect  in hi   (external power)
```

## Android BatteryService

```text
AC powered: true
USB powered: false
status: 2                  (charging)
present: true
level: 61
scale: 100
voltage: 7973 mV
current now: 1529531 uA
temperature: 277 (0.1 C)
```

The framework sees the same values, and Google services observed
`update battery state; isPlugged? true`. This is the charging indicator path.

## Assessment

Test B passes: charger insertion is detected from the BQ24617 DETECT/STAT
inputs, the gauge reports positive charging current, and Android switches to
AC-powered/Charging. Capacity moved 62 → 61 with a plausible charging voltage.

Known non-battery warnings:

```text
healthd: BatteryHealthPath not found
healthd: BatteryTechnologyPath not found
irq 59: nobody cared ... Disabling IRQ #59
```

The CPCAP IRQ storm/disable is the pre-existing power-key interrupt issue;
the power key still works through its 20 ms polling fallback. It is not part of
the battery driver.

## Missing evidence

No third capture exists after disconnecting the charger:

```text
artifacts/androidbattery79-report3
```

Test A already proves the disconnected state (online 0, Discharging, negative
current), but the **B → C transition after charging** has not been captured.
Test D extended monitoring is also not captured. Connect/disconnect without a
reboot and capture report3 for the transition proof.
