# LP2 power campaign

Use one boot and the same build for all measurements. Do not flash between the
three intervals. Every report is read-only and every wake is manual.

## 1. Screen-on idle

Leave Android on the home screen/display at the standard brightness.

```sh
sudo setfacl -m u:justin:rw /dev/ttyACM0
python3 scripts/capture-framed-diagnostic.py --output-dir artifacts/power-on-before \
  --storage-mode android44-readonly
sleep 600
python3 scripts/capture-framed-diagnostic.py --output-dir artifacts/power-on-after \
  --storage-mode android44-readonly
```

## 2. Screen-off awake (no LP2)

Short-press power to turn the display off. Do not trigger LP2.

```sh
python3 scripts/capture-framed-diagnostic.py --output-dir artifacts/power-off-before \
  --storage-mode android44-readonly
sleep 600
# short-press power to turn the display back on
python3 scripts/capture-framed-diagnostic.py --output-dir artifacts/power-off-after \
  --storage-mode android44-readonly
```

## 3. LP2 for 600 seconds

```sh
python3 scripts/capture-framed-diagnostic.py --output-dir artifacts/power-lp2-before \
  --storage-mode android44-readonly
python3 scripts/run-stage-test.py --stage lp2 --output-dir artifacts/power-lp2-cycle
# wait 600 seconds, then press the physical power button once
python3 scripts/run-stage-test.py --stage lp2 --status \
  --output-dir artifacts/power-lp2-status
python3 scripts/capture-framed-diagnostic.py --output-dir artifacts/power-lp2-after \
  --storage-mode android44-readonly
```

## Compare

```sh
python3 scripts/power-compare.py --label screen-on \
  --before artifacts/power-on-before/report-private.txt \
  --after artifacts/power-on-after/report-private.txt \
  --output artifacts/power-on.json

python3 scripts/power-compare.py --label screen-off \
  --before artifacts/power-off-before/report-private.txt \
  --after artifacts/power-off-after/report-private.txt \
  --output artifacts/power-off.json

python3 scripts/power-compare.py --label lp2 \
  --before artifacts/power-lp2-before/report-private.txt \
  --after artifacts/power-lp2-after/report-private.txt \
  --output artifacts/power-lp2.json
```

`current_now` is an instantaneous, noisy sample. The capacity/charge delta
over the full interval is the primary comparison. A gauge may be unreadable
while the PMIC/SPI path is asleep; the post-wake report is authoritative.

Do not run the campaign until Image 94's one-cycle physical-wake test passes.
