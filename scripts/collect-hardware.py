#!/usr/bin/env python3
"""Read-only collection from one authorized Wingray. Raw data stays local."""
from pathlib import Path
import os
import re
import struct
import subprocess
import json
import zlib
import base64
import shlex

root = Path(__file__).resolve().parents[1]
dest = root / 'artifacts/hardware-private'
dest.mkdir(parents=True, exist_ok=True)
serial = os.environ.get('ANDROID_SERIAL')
if not serial:
    devices = subprocess.check_output(['adb', 'devices'], text=True)
    found = [line.split()[0] for line in devices.splitlines() if line.endswith('\tdevice')]
    if len(found) != 1:
        raise SystemExit('Connect exactly one authorized Xoom or set ANDROID_SERIAL.')
    serial = found[0]
adb = ['adb', '-s', serial]
def shell(command):
    return subprocess.check_output(adb + ['shell', command]).replace(b'\r\n', b'\n')
def binary(command):
    # This tablet's Android 4.4 adbd predates exec-out. Base64 avoids the
    # legacy shell service's CRLF translation without writing on the tablet.
    encoded = shell(shlex.join(command) + ' 2>/dev/null | /system/xbin/busybox base64')
    return base64.b64decode(b''.join(encoded.split()), validate=True)
if shell('getprop ro.product.device').strip() != b'wingray':
    raise SystemExit('Connected device is not Wingray.')
commands = {
 'cmdline.txt': 'cat /proc/cmdline',
 'partitions.txt': 'cat /proc/partitions',
 'input-devices.txt': 'cat /proc/bus/input/devices',
 'pinmux.txt': 'cat /sys/kernel/debug/tegra_pinmux',
 'pinmux-drive.txt': 'cat /sys/kernel/debug/tegra_pinmux_drive',
 'gpio.txt': 'cat /sys/kernel/debug/gpio',
 'iomem.txt': 'cat /proc/iomem',
 'dmesg.txt': 'dmesg',
 'mounts.txt': 'cat /proc/mounts',
 'regulators.txt': 'for p in /sys/class/regulator/regulator.*; do echo "$p"; cat "$p/name" "$p/microvolts" "$p/state" 2>/dev/null; done',
 'peripherals.txt': 'for p in /sys/bus/i2c/devices/*-00*/name; do echo "$p"; cat "$p"; done; ls /sys/class/leds; cat /sys/class/graphics/fb0/modes',
 'geometry.txt': 'for p in /sys/block/mmcblk0/mmcblk0p*; do echo "$p"; cat "$p/start" "$p/size"; done',
}
for name, command in commands.items():
    (dest / name).write_bytes(shell(command))
config = binary(['cat', '/proc/config.gz'])
(dest / 'config.gz').write_bytes(config)
import gzip
(dest / 'kernel.config').write_bytes(gzip.decompress(config))
cmdline = (dest / 'cmdline.txt').read_text()
sector = int(re.search(r'\bgpt_sector=(0x[0-9a-fA-F]+|[0-9]+)', cmdline)[1], 0)
header = binary(['dd', 'if=/dev/block/mmcblk0', 'bs=512', f'skip={sector}', 'count=1'])
assert len(header) == 512 and header[:8] == b'EFI PART', 'No GPT at firmware location'
(dest / 'gpt-header.bin').write_bytes(header)
header_size, checksum = struct.unpack_from('<II', header, 12)
checked = bytearray(header[:header_size]); checked[16:20] = b'\0' * 4
assert zlib.crc32(checked) == checksum, 'GPT header CRC mismatch'
entries_lba, count, size, entries_crc = struct.unpack_from('<QIII', header, 72)
assert 0 < count <= 1024 and 128 <= size <= 1024
entries = binary(['dd', 'if=/dev/block/mmcblk0', 'bs=512', f'skip={entries_lba}', f'count={(count*size+511)//512}'])[:count*size]
assert zlib.crc32(entries) == entries_crc, 'GPT entries CRC mismatch'
(dest / 'gpt-entries.bin').write_bytes(entries)
parts = []
for i in range(count):
    entry = entries[i*size:(i+1)*size]
    if entry[:16] == b'\0'*16:
        continue
    start, end = struct.unpack_from('<QQ', entry, 32)
    label = entry[56:128].decode('utf-16-le').split('\0')[0]
    parts.append({'number': i+1, 'label': label, 'start': start, 'size': end-start+1})
(dest / 'gpt-layout.json').write_text(json.dumps({'header_lba':sector, 'partitions':parts}, indent=2)+'\n')
# Back up only boot/recovery partitions identified by GPT labels, never data.
for part in parts:
    if part['label'].lower() not in ('boot', 'recovery', 'lnx', 'sos'):
        continue
    assert part['size'] <= 65536, 'Unexpected boot partition size'
    image = binary(['dd', f"if=/dev/block/mmcblk0p{part['number']}", 'bs=512', f"count={part['size']}"])
    assert len(image) == part['size']*512
    (dest / f"backup-{part['label']}.img").write_bytes(image)
print('Read-only hardware capture and verified GPT saved locally under artifacts/hardware-private.')
print('Do not upload this raw directory: it includes identifiers and runtime logs.')
print('Partition labels:', ', '.join(p['label'] for p in parts))
