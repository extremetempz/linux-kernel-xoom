#!/usr/bin/env python3
"""Fetch the pinned official static BusyBox for standalone RAM diagnostics."""
from pathlib import Path
import hashlib,json,urllib.request
root=Path(__file__).resolve().parents[1]
url='https://busybox.net/downloads/binaries/1.31.0-defconfig-multiarch-musl/busybox-armv5l'
expected='69bbb65ccd70481ec2df19b8770b2e979aeb75dddf08d2fc5b0230f892989c40'
target=root/'artifacts/busybox-static-armv5l'
if target.exists():
    data=target.read_bytes()
else:
    with urllib.request.urlopen(url,timeout=60) as response:
        data=response.read(2*1024*1024)
assert hashlib.sha256(data).hexdigest()==expected, 'Static runtime hash mismatch; preserve existing files and investigate'
target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():
    with target.open('xb') as stream:stream.write(data)
metadata={'url':url,'sha256':expected,'version':'1.31.0','architecture':'ARMv5T, VFPv2, no NEON (ELF attributes)','linkage':'static musl; no Android property-service dependency','license':'GPL-2.0-only','source_url':'https://busybox.net/downloads/busybox-1.31.0.tar.bz2','hash_note':'Pinned from the reviewed official HTTPS download; not an independently verified upstream signature.'}
(target.parent/'busybox-static-provenance.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Verified pinned official static ARM diagnostic runtime:',target)
