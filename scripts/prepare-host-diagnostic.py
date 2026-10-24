#!/usr/bin/env python3
"""Package a host-only RAM diagnostic; never contacts or flashes a device."""
from pathlib import Path
import argparse, gzip, hashlib, json, os, stat, struct, subprocess, sys
from android44_image import Entry, parse_newc, pack_newc
from host_test import validate_artifacts
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--kernel-dir',type=Path,required=True)
p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args();kernel=a.kernel_dir.resolve();out=a.output_dir.resolve()
assert out.is_relative_to(root/'artifacts') and not out.exists()
validate_artifacts(kernel)
# Preserve both originals, and reject an unexpected boot template before use.
expected={'boot':'64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588',
          'recovery':'5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606'}
for name,sha in expected.items():
    assert hashlib.sha256((root/f'artifacts/hardware-private/backup-{name}.img').read_bytes()).hexdigest()==sha
subprocess.run([sys.executable,str(root/'scripts/prepare-diagnostic.py'),'--kernel-dir',str(kernel),'--output-dir',str(out)],check=True)
entries=parse_newc(gzip.decompress((out/'ramdisk.cpio.gz').read_bytes()))
report=entries['bin/diagnostic-report'];anchor=b"/bin/busybox printf 'XOOM_DMESG_BEGIN"
assert report.data.count(anchor)==1
entries[report.name]=Entry(report.name,report.mode,report.data.replace(anchor,b'/bin/busybox sh /bin/host-test-report\n'+anchor))
entries['bin/host-test-report']=Entry('bin/host-test-report',stat.S_IFREG|0o755,(root/'diagnostic/host-test-report.sh').read_bytes())
ramdisk=gzip.compress(pack_newc(entries),mtime=0)
base=(out/'wingray-diagnostic.img').read_bytes();header=bytearray(base[:2048]);k=(kernel/'zImage-dtb').read_bytes()
assert struct.unpack_from('<I',header,36)[0]==2048
struct.pack_into('<I',header,16,len(ramdisk))
h=hashlib.sha1()
for data in (k,ramdisk,b''):h.update(data);h.update(struct.pack('<I',len(data)))
header[576:596]=h.digest()
image=bytes(header)+k+b'\0'*(-len(k)%2048)+ramdisk+b'\0'*(-len(ramdisk)%2048)
assert len(image)<8*1024*1024
(out/'wingray-diagnostic.img').rename(out/'base-diagnostic.img')
(out/'ramdisk.cpio.gz').rename(out/'base-ramdisk.cpio.gz')
(out/'wingray-host-diagnostic.img').write_bytes(image)
(out/'host-ramdisk.cpio.gz').write_bytes(ramdisk)
# Validate the newly packed header, addresses, digest and exact payloads.
second_address=struct.unpack_from('<I',(root/'artifacts/hardware-private/backup-boot.img').read_bytes(),28)[0]
assert struct.unpack_from('<8I',image,8)==(len(k),0x10008000,len(ramdisk),0x11000000,0,second_address,0x10000100,2048)
assert image[2048:2048+len(k)]==k
assert parse_newc(gzip.decompress(ramdisk))['init'].data==entries['init'].data
assert not any(n.startswith('system/lib/') for n in entries)
manifest={'purpose':'host1x clock/IRQ activation only; no GPU commands or accelerated Android',
          'sha256':hashlib.sha256(image).hexdigest(),'size':len(image),'kernel_sha256':hashlib.sha256(k).hexdigest(),
          'original_backup_hashes':expected,'physical_execution':False,'storage_mounts':[],
          'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['scripts/prepare-host-diagnostic.py','scripts/host_test.py','diagnostic/host-test-report.sh']}}
with (out/'host-manifest.json').open('x') as f:f.write(json.dumps(manifest,indent=2)+'\n');f.flush();os.fsync(f.fileno())
for name,sha in expected.items():assert hashlib.sha256((root/f'artifacts/hardware-private/backup-{name}.img').read_bytes()).hexdigest()==sha
print('Prepared host-only boot image; not flashed:',out/'wingray-host-diagnostic.img')
