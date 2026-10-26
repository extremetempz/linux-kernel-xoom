# Battery 79 — Test A result

26 October 2026. Charger disconnected. Report:
`artifacts/androidbattery79-report1/report-private.txt` (integrity verified).

## Kernel power_supply

```text
ac:
  type = Mains
  online = 0

battery:
  type = Battery
  present = 1
  capacity = 62
  status = Discharging
  voltage_now = 7642080 uV   (7.64208 V)
  current_now = -358906 uA   (discharging)
  temp = 275                 (27.5 C)
```

Charger GPIOs:

```text
gpio-25  wingray-stat2   in hi
gpio-173 wingray-stat1   in hi
gpio-174 wingray-detect  in lo
```

OWR/DS2781 probe:

```text
tegra_w1 ... irq 58
ds2781-battery ds2781-battery.0: DS2781/BQ24617 P3 read-only monitor, 2s polling
```

## Android BatteryService

```text
AC powered: false
USB powered: false
status: 3                  (discharging)
present: true
level: 62
scale: 100
voltage: 7642 mV
current now: -358906 uA
temperature: 275 (0.1 C)
```

`healthd` is running, `PowerManagerService.mBatteryLevel=62`, and Android
reports `battery_monitor_enumerated` before framework start.

## Assessment

Test A passes: real gauge capacity, voltage, current and temperature reach
both the standard Linux power_supply class and Android BatteryService. The
percentage is not voltage-estimated.

Minor warnings:

```text
healthd: BatteryHealthPath not found
healthd: BatteryTechnologyPath not found
```

`health`/`technology` are not exported yet; Android falls back to unknown
health and blank technology. This does not affect percentage or charging
state, but `health` is supported by the gauge temperature and remains a small
follow-up.

The diagnostic wrapper still marks the report `state: failed` with
`ProtocolError: Unexpected filesystem or mount path`, while
`report_integrity` is `verified`. This is the existing report-path validator,
not a battery measurement error.

## Still required

- Test B: connect the original charger; expect `ac/online=1`, charging/full/
  not-charging status, Android AC powered and charging icon.
- Test C: disconnect; expect online 0 and Discharging again without reboot.
- Test D: extended monitoring, plausible percentage movement, no persistent
  OWR/I2C errors or crashes.
