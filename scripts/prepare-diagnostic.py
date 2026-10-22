#!/usr/bin/env python3
"""Build a new local diagnostic image; never overwrite evidence or flash a device."""
from pathlib import Path
import argparse, gzip, hashlib, json, re, stat, struct, subprocess
root = Path(__file__).resolve().parents[1]
private = root / 'artifacts/hardware-private'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True,
                    help='New directory under artifacts/; existing directories are refused')
parser.add_argument('--kernel-dir', type=Path, default=root/'artifacts/wingray44')
runtime = parser.add_mutually_exclusive_group()
runtime.add_argument('--static-busybox', type=Path,
                    default=root/'artifacts/busybox-static-armv5l',
                    help='Static ARM BusyBox (default: pinned standalone diagnostic runtime)')
runtime.add_argument('--android-runtime', action='store_true',
                    help='Reproduce the historical property-workspace-dependent Android runtime')
parser.add_argument('--panic-seconds', type=int, default=0,
                    help='Default 0 preserves a panic for inspection instead of rebooting')
parser.add_argument('--legacy-shell', action='store_true',
                    help='Reproduce the historical unsolicited report/interactive shell (not the default framed reporter)')
parser.add_argument('--panelbus', action='store_true', help='Include fixed Wingray panel-bus readback; requires the isolated panelbus kernel')
parser.add_argument('--display', action='store_true', help='Include one-shot framebuffer color bars and read-only metadata; requires the display kernel')
args = parser.parse_args()
if (args.panelbus or args.display) and (args.legacy_shell or args.android_runtime):
    parser.error('Hardware readback requires the framed standalone diagnostic')
if args.panelbus and args.display:
    parser.error('Display owns the backlight bus; raw panel-bus readback is excluded')
if args.android_runtime:
    args.static_busybox = None
    args.legacy_shell = True
elif not args.static_busybox.is_file():
    parser.error('Static runtime missing. Run python3 scripts/fetch-diagnostic-runtime.py first.')
if not 0 <= args.panic_seconds <= 3600:
    parser.error('panic-seconds must be between 0 and 3600')
out = args.output_dir.resolve()
if not out.is_relative_to((root/'artifacts').resolve()):
    parser.error('Keep the proprietary diagnostic runtime under ignored artifacts/.')
if out.exists():
    parser.error('Output already exists; preserved test images must not be overwritten.')
backup = (private / 'backup-boot.img').read_bytes()
assert backup[:8] == b'ANDROID!'
ks, ka, rs, ra, ss, sa, tags, page = struct.unpack_from('<8I', backup, 8)
assert (ka, ra, tags, page) == (0x10008000, 0x11000000, 0x10000100, 2048)
assert ss == 0
kernel = (args.kernel_dir / 'zImage-dtb').read_bytes()
if args.static_busybox:
    busybox = args.static_busybox.resolve()
    elf = busybox.read_bytes()
    assert elf[:7] == b'\x7fELF\x01\x01\x01' and struct.unpack_from('<H',elf,18)[0] == 40, 'Require little-endian ELF32 ARM'
    headers = subprocess.check_output(['readelf','-lW',str(busybox)],text=True)
    dynamic = subprocess.check_output(['readelf','-dW',str(busybox)],text=True)
    attributes = subprocess.check_output(['readelf','-A',str(busybox)],text=True)
    assert 'INTERP' not in headers and '(NEEDED)' not in dynamic, 'Require a static runtime without an interpreter or shared libraries'
    assert 'Tag_CPU_arch: v5T' in attributes and 'Tag_Advanced_SIMD_arch:' not in attributes, 'Require the reviewed non-NEON ARMv5T runtime'
    files = {'bin/busybox': busybox}
    pending = []
else:
    # Historical Android runtime, retained for reproducing earlier images.
    # It requires an Android property workspace; use static mode for the
    # standalone diagnostic which does not start Android's init service.
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
if args.legacy_shell:
    diagnostic_files = {'init': init, 'bin/report': report}
else:
    diagnostic_files = {
        'init': (root/'diagnostic/init.sh').read_bytes(),
        'bin/diagnostic-server': (root/'diagnostic/server.sh').read_bytes(),
        'bin/diagnostic-report': (root/'diagnostic/report.sh').read_bytes(),
    }
if args.panelbus:
    config = (args.kernel_dir/'kernel.config').read_text()
    assert 'CONFIG_LOCALVERSION="-wingray-panelbus"' in config
    for option in ['I2C_CHARDEV', 'I2C_TEGRA', 'REGULATOR_FIXED_VOLTAGE']:
        assert f'CONFIG_{option}=y' in config
    assert b'i2cget\0' in (files['bin/busybox']).read_bytes(), 'Pinned runtime must include i2cget'
    diagnostic_files['bin/panelbus-report'] = (root/'diagnostic/panelbus-report.sh').read_bytes()
if args.display:
    subprocess.run(['python3',str(root/'scripts/verify-kernel.py'),str(args.kernel_dir),'display'],check=True)
    pattern=args.kernel_dir/'display-pattern'
    manifest=json.loads((args.kernel_dir/'display-pattern-manifest.json').read_text())
    assert hashlib.sha256(pattern.read_bytes()).hexdigest() == manifest['sha256']
    assert hashlib.sha256((root/'diagnostic/display-pattern.c').read_bytes()).hexdigest() == manifest['source_sha256']
    ph=subprocess.check_output(['readelf','-lW',str(pattern)],text=True)
    pd=subprocess.check_output(['readelf','-dW',str(pattern)],text=True)
    pa=subprocess.check_output(['readelf','-A',str(pattern)],text=True)
    assert 'INTERP' not in ph and '(NEEDED)' not in pd
    assert 'Tag_CPU_arch: v7' in pa and 'Tag_Advanced_SIMD_arch:' not in pa
    files['bin/display-pattern']=pattern
    diagnostic_files['bin/display-start']=(root/'diagnostic/display-start.sh').read_bytes()
    diagnostic_files['bin/display-report']=(root/'diagnostic/display-report.sh').read_bytes()
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
for name, data in diagnostic_files.items():add(name,stat.S_IFREG|0o755,data)
add('bin/sh',stat.S_IFLNK|0o777,b'busybox')
add('TRAILER!!!',0)
ramdisk = gzip.compress(bytes(archive),mtime=0)
assert len(kernel)<ra-ka, 'Kernel overlaps ramdisk load address'
# v0 header with measured addresses, no device identifiers or inherited ROM init.
header = bytearray(page)
header[:8] = b'ANDROID!'
struct.pack_into('<10I',header,8,len(kernel),ka,len(ramdisk),ra,0,sa,tags,page,0,0)
header[48:48+len(b'wingray-diag')] = b'wingray-diag'
cmd = f'androidboot.carrier=wifi-only product_type=w rdinit=/init panic={args.panic_seconds}'.encode()
if args.display:
    cmd += b' drm.debug=0x06'
header[64:64+len(cmd)] = cmd
h = hashlib.sha1()
for data in (kernel,ramdisk,b''):
 h.update(data);h.update(struct.pack('<I',len(data)))
header[576:596] = h.digest()
def padded(data):return data+b'\0'*(-len(data)%page)
image = bytes(header)+padded(kernel)+padded(ramdisk)
out.mkdir(parents=True, exist_ok=False)
(out/'wingray-diagnostic.img').write_bytes(image)
(out/'ramdisk.cpio.gz').write_bytes(ramdisk)
(out/'manifest.json').write_text(json.dumps({'purpose':'experimental diagnostic image; builder performs no device operations','kernel_address':hex(ka),'ramdisk_address':hex(ra),'tags_address':hex(tags),'page_size':page,'size':len(image),'sha256':hashlib.sha256(image).hexdigest(),'runtime_kind':'static-armv5t' if args.static_busybox else 'copied-android','diagnostic_transport':'legacy-shell' if args.legacy_shell else 'framed-v2','diagnostic_sources_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in diagnostic_files.items()},'kernel_sha256':hashlib.sha256(kernel).hexdigest(),'runtime_files':sorted(files),'runtime_sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()},'storage_mounts':[], 'bootloader_note':'Xoom consumer bootloader 1050 rejects fastboot boot; boot-partition tests require user authorization'},indent=2)+'\n')
print('Prepared local-only image:',out/'wingray-diagnostic.img')
print('SHA256:',hashlib.sha256(image).hexdigest())
