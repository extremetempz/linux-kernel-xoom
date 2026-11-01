#!/usr/bin/env python3
"""Compare two read-only Wingray reports for an LP2 power campaign.

Usage:
  power-compare.py --before old/report-private.txt --after new/report-private.txt \
      --label lp2 --output result.json

The reports include XOOM_DISPLAY_POWER_V1 (uptime, display state) and the
XOOM_BATTERY_MONITOR_V1 snapshot. This tool never contacts the device.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

PROPS = ('capacity', 'voltage_now', 'current_now', 'charge_counter',
         'energy_now', 'power_now', 'status')

def parse_report(path: Path) -> dict:
    text = path.read_text(errors='replace')
    out = {'path': str(path), 'battery': {}, 'supplies': {}}
    m = re.search(r'^XOOM_UPTIME_START ([0-9.]+) ([0-9.]+)', text, re.M)
    if m:
        out['uptime'] = float(m.group(1))
        out['uptime_idle'] = float(m.group(2))
    current = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('SUPPLY '):
            current = line.split(' ', 1)[1].strip()
            out['supplies'][current] = {}
        elif line.startswith('PROPERTY ') and current:
            prop = line.split(' ', 1)[1].strip()
            if prop in PROPS and i + 1 < len(lines):
                val = lines[i + 1].strip()
                out['supplies'][current][prop] = val
    out['battery'] = out['supplies'].get('battery', {})
    return out

def number(d: dict, key: str):
    v = d.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before', type=Path, required=True)
    ap.add_argument('--after', type=Path, required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        ap.error('refusing to overwrite output')
    b, c = parse_report(a.before), parse_report(a.after)
    if 'uptime' not in b or 'uptime' not in c:
        ap.error('reports do not contain XOOM_UPTIME_START')
    seconds = c['uptime'] - b['uptime']
    if seconds <= 0:
        ap.error('uptime did not advance; reports may be reversed or same boot')
    bb, cc = b['battery'], c['battery']
    cap0, cap1 = number(bb, 'capacity'), number(cc, 'capacity')
    volt0, volt1 = number(bb, 'voltage_now'), number(cc, 'voltage_now')
    cur0, cur1 = number(bb, 'current_now'), number(cc, 'current_now')
    # current_now is typically uA on this gauge; keep raw units and label it.
    result = {
        'label': a.label,
        'before': str(a.before), 'after': str(a.after),
        'seconds': round(seconds, 3),
        'uptime_before': b.get('uptime'), 'uptime_after': c.get('uptime'),
        'capacity_before': cap0, 'capacity_after': cap1,
        'capacity_delta': None if cap0 is None or cap1 is None else cap1 - cap0,
        'voltage_before': volt0, 'voltage_after': volt1,
        'current_before': cur0, 'current_after': cur1,
        'battery_status_before': bb.get('status'), 'battery_status_after': cc.get('status'),
        'charge_counter_before': bb.get('charge_counter'),
        'charge_counter_after': cc.get('charge_counter'),
        'energy_before': bb.get('energy_now'), 'energy_after': cc.get('energy_now'),
        'collected_utc': datetime.now(timezone.utc).isoformat(),
        'note': 'Instantaneous current is noisy; use capacity/charge over the full interval.',
    }
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
