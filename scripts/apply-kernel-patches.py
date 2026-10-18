#!/usr/bin/env python3
"""Apply the reviewed Wingray series to its pinned donor without resetting work."""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[1]
source = next(s for s in json.loads((root / 'sources.lock.json').read_text()) if s['name'] == 'donor')
tree = root / source['path']
subprocess.run(['git', '-C', str(tree), 'merge-base', '--is-ancestor', source['commit'], 'HEAD'], check=True)
for patch in sorted((root / 'kernel/patches').glob('*.patch')):
    command = ['git', '-C', str(tree), 'apply']
    if subprocess.run(command + ['--reverse', '--check', str(patch)], capture_output=True).returncode == 0:
        print(f'Already applied: {patch.name}')
        continue
    subprocess.run(command + ['--check', str(patch)], check=True)
    subprocess.run(command + [str(patch)], check=True)
    print(f'Applied: {patch.name}')
