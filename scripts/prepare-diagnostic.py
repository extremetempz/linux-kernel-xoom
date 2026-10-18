#!/usr/bin/env python3
"""Build a local-only diagnostic Android boot image. Never flashes a device."""
from pathlib import Path
import gzip, hashlib, json, re, stat, struct, subprocess
root = Path(__file__).resolve().parents[1]
private = root / 'artifacts/hardware-private'
out = root / 'artifacts/diagnostic'
out.mkdir(exist_ok=True)
backup = (private / 'backup-boot.img').read_bytes()
assert backup[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, tags, page = struct.unpack_from('<8I', backup, 8)
assert (ka, ra, tags, page) == (0x10008000, 0x11000000, 0x10000100, 2048)
assert ss == 0
kernel = (root / 'artifacts/wingray44/zImage-dtb').read_bytes()
# Dependency closure from the tablet's own BusyBox, never the host's libraries.
files = {'bin/busybox': private/'busybox', 'system/bin/linker': private/'linker'}
pending = [private/'busybox', private/'linker']
while pending:
    elf = pending.pop()
    for lib in re.findall(r'Shared library: \[([^\]]+)\]', subprocess.check_output(['readelf','-d',str(elf)],text=True)):
        name = 'system/lib/'+lib
        if name not in files:
            path = private/'system-lib'/lib
            if not path.is_file(): raise SystemExit('Missing runtime dependency: '+str(path))
            files[name] = path
            pending.append(path)
init = b'''#!/bin/busybox sh
export PATH=/bin:/system/bin
export LD_LIBRARY_PATH=/system/lib
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t devtmpfs devtmpfs /dev
/bin/busybox mkdir -p /dev/pts /run /tmp
/bin/busybox mount -t tmpfs tmpfs /run
/bin/busybox mount -t tmpfs tmpfs /tmp
/bin/busybox mount -t devpts devpts /dev/pts
/bin/busybox mount -t debugfs debugfs /sys/kernel/debug
/bin/busybox sh /bin/report > /run/boot-report.txt 2>&1
while :; do
 if [ -c /dev/ttyGS0 ]; then
  /bin/busybox sh -c '/bin/busybox cat /run/boot-report.txt; echo "Wingray RAM diagnostic shell. Android partitions are unmounted."; exec /bin/busybox sh -i' < /dev/ttyGS0 > /dev/ttyGS0 2>&1
 fi
 /bin/busybox sleep 1
done
'''
report = b'''#!/bin/busybox sh
echo XOOM_DIAGNOSTIC_BEGIN
/bin/busybox uname -a
/bin/busybox cat /proc/cmdline /proc/meminfo /proc/partitions
/bin/busybox cat /proc/bus/input/devices
/bin/busybox ls -l /sys/class/backlight /sys/class/drm /sys/class/net /sys/bus/sdio/devices
for p in /sys/class/regulator/regulator.*; do
 echo "$p"; /bin/busybox cat "$p/name" "$p/microvolts" "$p/state" 2>/dev/null
done
for p in /sys/block/mmcblk*/mmcblk*p*; do
 echo "$p"; /bin/busybox cat "$p/start" "$p/size"
done
/bin/busybox dmesg
echo XOOM_DIAGNOSTIC_END
'''
archive = bytearray(); ino = 0
def add(name, mode, data=b'', major=0, minor=0):
 global ino
 ino += 1
 name = name.encode()+b'\0'
 fields = [ino,mode,0,0,1,0,len(data),0,0,major,minor,len(name),0]
 archive.extend(b'070701'+b''.join(f'{v:08x}'.encode() for v in fields))
 archive.extend(name); archive.extend(b'\0'*(-len(archive)%4))
 archive.extend(data); archive.extend(b'\0'*(-len(archive)%4))
for d in ['bin','system','system/bin','system/lib','dev','dev/pts','proc','sys','run','tmp']:
 add(d, stat.S_IFDIR|0o755)
add('dev/console',stat.S_IFCHR|0o600,major=5,minor=1)
add('dev/null',stat.S_IFCHR|0o666,major=1,minor=3)
for name, path in sorted(files.items()):add(name,stat.S_IFREG|0o755,path.read_bytes())
add('init',stat.S_IFREG|0o755,init)
add('bin/report',stat.S_IFREG|0o755,report)
add('bin/sh',stat.S_IFLNK|0o777,b'busybox')
add('TRAILER!!!',0)
ramdisk = gzip.compress(bytes(archive),mtime=0)
assert len(kernel)<ra-ka, 'Kernel overlaps ramdisk load address'
# v0 header with measured addresses, no device identifiers or inherited ROM init.
header = bytearray(page)
header[:8] = b'ANDROID!'
struct.pack_into('<10I',header,8,len(kernel),ka,len(ramdisk),ra,0,sa,tags,page,0,0)
header[48:48+len(b'wingray-diag')] = b'wingray-diag'
cmd = b'androidboot.carrier=wifi-only product_type=w rdinit=/init panic=30'
header[64:64+len(cmd)] = cmd
h = hashlib.sha1()
for data in (kernel,ramdisk,b''):
 h.update(data);h.update(struct.pack('<I',len(data)))
header[576:596] = h.digest()
def padded(data):return data+b'\0'*(-len(data)%page)
image = bytes(header)+padded(kernel)+padded(ramdisk)
(out/'wingray-diagnostic.img').write_bytes(image)
(out/'ramdisk.cpio.gz').write_bytes(ramdisk)
(out/'manifest.json').write_text(json.dumps({'purpose':'temporary RAM boot only; no flashing','kernel_address':hex(ka),'ramdisk_address':hex(ra),'tags_address':hex(tags),'page_size':page,'size':len(image),'sha256':hashlib.sha256(image).hexdigest(),'runtime_files':sorted(files),'storage_mounts':[]},indent=2)+'\n')
print('Prepared local-only image:',out/'wingray-diagnostic.img')
print('SHA256:',hashlib.sha256(image).hexdigest())
