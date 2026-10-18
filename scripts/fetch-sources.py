#!/usr/bin/env python3
"""Fetch exact upstream commits without overwriting existing checkouts."""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
for source in json.loads((root / 'sources.lock.json').read_text()):
    path = root / source['path']
    if path.exists():
        head = subprocess.run(['git', '-C', str(path), 'rev-parse', '--verify', 'HEAD'], text=True, capture_output=True)
        if head.returncode == 0 and head.stdout.strip() != source['commit']:
            ancestry = subprocess.run(['git', '-C', str(path), 'merge-base', '--is-ancestor', source['commit'], 'HEAD'])
            if ancestry.returncode != 0:
                raise SystemExit(f'{path}: unexpected HEAD; preserve local work and inspect manually')
            print(f"Preserving development commits: {source['name']}")
            continue
        if head.returncode == 0:
            print(f"Already present: {source['name']}")
            continue
        origin = subprocess.check_output(['git', '-C', str(path), 'remote', 'get-url', 'origin'], text=True).strip()
        if origin != source['url']:
            raise SystemExit(f'{path}: unexpected origin; inspect manually')
    else:
        path.mkdir(parents=True)
        subprocess.run(['git', 'init', str(path)], check=True)
        subprocess.run(['git', '-C', str(path), 'remote', 'add', 'origin', source['url']], check=True)
    subprocess.run(['git', '-C', str(path), 'fetch', '--depth=1', 'origin', source['commit']], check=True)
    subprocess.run(['git', '-C', str(path), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
