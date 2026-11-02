"""Offline, narrowly scoped transforms for the first Wingray Android experiment.

This module never executes ramdisk content or contacts a device. The caller must
pin the original boot image before passing its archive to these transforms.
"""
from dataclasses import dataclass, replace
import gzip
import hashlib
from pathlib import PurePosixPath
import shlex
import stat
import struct

BOOT_SHA256 = '64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588'
BUSYBOX_SHA256 = '69bbb65ccd70481ec2df19b8770b2e979aeb75dddf08d2fc5b0230f892989c40'
SERVICES = {'ueventd', 'healthd', 'servicemanager', 'vold', 'netd', 'debuggerd',
            'surfaceflinger', 'zygote', 'drm', 'media', 'keystore', 'installd', 'sdcard'}
ACTIONS = {'early-init', 'init', 'post-fs', 'post-fs-data', 'boot', 'nonencrypted'}
COMMANDS = {'write', 'mkdir', 'chown', 'chmod', 'symlink', 'setprop', 'setrlimit', 'setcon',
            'export', 'ifup', 'hostname', 'domainname', 'sysclktz', 'loglevel',
            'restorecon', 'restorecon_recursive', 'copy', 'class_start', 'start', 'mount'}
UIDS = {'root': 0, 'system': 1000, 'graphics': 1003, 'drm': 1019,
        'media': 1013, 'keystore': 1017}


def digest(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Entry:
    name: str
    mode: int
    data: bytes = b''
    uid: int = 0
    gid: int = 0
    major: int = 0
    minor: int = 0


def parse_newc(data):
    """Bounded parser; never extract paths, follow symlinks or resolve hardlinks."""
    if len(data) > 16 * 1024 * 1024:
        raise ValueError('Ramdisk archive exceeds the reviewed bound')
    entries, pos = {}, 0
    while True:
        if data[pos:pos + 6] != b'070701' or pos + 110 > len(data):
            raise ValueError('Malformed newc header')
        try:
            fields = [int(data[pos + 6 + i * 8:pos + 14 + i * 8], 16) for i in range(13)]
        except ValueError as exc:
            raise ValueError('Non-hex newc header') from exc
        _, mode, uid, gid, nlink, _, size, _, _, major, minor, namesize, check = fields
        if not 1 <= namesize <= 256 or check != 0:
            raise ValueError('Invalid newc name/checksum')
        start = pos + 110
        name_raw = data[start:start + namesize]
        if len(name_raw) != namesize or name_raw[-1:] != b'\0' or b'\0' in name_raw[:-1]:
            raise ValueError('Truncated or ambiguous newc name')
        name = name_raw[:-1].decode('ascii')
        pos = (start + namesize + 3) & ~3
        if size > len(data) - pos:
            raise ValueError('Truncated newc payload')
        payload = data[pos:pos + size]
        pos = (pos + size + 3) & ~3
        if name == 'TRAILER!!!':
            if size or any(data[pos:]):
                raise ValueError('Unexpected archive trailer or concatenated archive')
            return entries
        path = PurePosixPath(name)
        if (not name or name.startswith('/') or '..' in path.parts or
                (name != '.' and str(path) != name) or name in entries):
            raise ValueError('Unsafe, noncanonical or duplicate archive path')
        kind = stat.S_IFMT(mode)
        if kind not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK, stat.S_IFCHR):
            raise ValueError('Unreviewed archive entry type')
        if kind == stat.S_IFREG and nlink != 1:
            raise ValueError('Hardlinked regular files are unsupported')
        if kind in (stat.S_IFDIR, stat.S_IFCHR) and size:
            raise ValueError('Unexpected archive payload')
        entries[name] = Entry(name, mode, payload, uid, gid, major, minor)


def pack_newc(entries):
    archive = bytearray()
    for ino, entry in enumerate([*entries.values(), Entry('TRAILER!!!', 0)], 1):
        name = entry.name.encode('ascii') + b'\0'
        fields = (ino, entry.mode, entry.uid, entry.gid, 1, 0, len(entry.data), 0, 0,
                  entry.major, entry.minor, len(name), 0)
        archive.extend(b'070701' + b''.join(f'{value:08x}'.encode() for value in fields))
        archive.extend(name)
        archive.extend(b'\0' * (-len(archive) % 4))
        archive.extend(entry.data)
        archive.extend(b'\0' * (-len(archive) % 4))
    return bytes(archive)


def original_entries(boot):
    if digest(boot) != BOOT_SHA256 or boot[:8] != b'ANDROID!':
        raise ValueError('Original boot image hash mismatch')
    ks, ka, rs, ra, ss, _, tags, page = struct.unpack_from('<8I', boot, 8)
    if (ka, ra, tags, page, ss) != (0x10008000, 0x11000000, 0x10000100, 2048, 0):
        raise ValueError('Unexpected original boot layout')
    offset = page + (ks + page - 1) // page * page
    compressed = boot[offset:offset + rs]
    # gzip.decompress is bounded by the pinned original input hash above.
    return parse_newc(gzip.decompress(compressed))


def sections(text):
    """Parse the reviewed init syntax; indentation does not change import scope."""
    result, current = [], None
    for line in text.splitlines():
        content = line.split('#', 1)[0].strip()
        if not content or content.startswith('import '):
            continue
        if content.startswith(('on ', 'service ')):
            current = [content, []]
            result.append(current)
        elif current is None:
            raise ValueError('Command outside an init section')
        else:
            current[1].append(content)
    return result


def transform_init(original):
    """Preserve generic RAM setup and an explicit service whitelist only."""
    output = ['# Generated experimental Android init; persistent media is read-only.',
              'import /init.environ.rc', 'import /init.xoom-firstboot.rc', '']
    kept, log_uids = set(), {}
    for header, commands in sections(original):
        tokens = shlex.split(header)
        if tokens[0] == 'service':
            name = tokens[1]
            if name not in SERVICES or name == 'sdcard':
                continue
            if name in kept:
                raise ValueError('Duplicate retained service')
            kept.add(name)
            if name != 'ueventd':
                # Android init drops uid/gid BEFORE exec; create logs for that UID.
                users = [shlex.split(c)[1] for c in commands if c.startswith('user ')]
                user = users[0] if users else 'root'
                if len(users) > 1 or user not in UIDS:
                    raise ValueError('Unreviewed service UID')
                log_uids[name] = (user, UIDS[user])
                tokens[2:2] = ['/bin/android-service-runner', name]
            output.append(' '.join(tokens))
            for command in commands:
                option = command.split()[0]
                if option == 'critical':
                    continue  # No automatic reboot to recovery after service crashes.
                if option not in {'class', 'user', 'group', 'socket', 'ioprio',
                                  'seclabel', 'onrestart', 'disabled', 'oneshot'}:
                    raise ValueError('Unreviewed service option: ' + command)
                if command.startswith('onrestart write '):
                    continue  # Legacy power controls do not describe this kernel.
                if command.startswith('onrestart restart ') and command.split()[-1] not in SERVICES:
                    raise ValueError('Restart outside retained service set')
                output.append('    ' + command)
            output.append('')
            continue
        trigger = header[3:]
        if trigger not in ACTIONS:
            continue
        output.append(header)
        for command in commands:
            parts = shlex.split(command)
            if parts[0] not in COMMANDS:
                raise ValueError('Unreviewed init command: ' + command)
            if any(x in command for x in ('/sys/fs/cgroup/memory', '/selinux',
                                         '/sys/fs/selinux', '/sys/fs/pstore', '/proc/apanic')):
                continue
            if command.startswith('mount tmpfs none /sys/fs/cgroup '):
                continue  # Memory cgroups are disabled in this isolated profile.
            if parts[0] in {'start', 'class_start'}:
                if parts[0] == 'start' and parts[1] != 'ueventd':
                    raise ValueError('Unexpected explicit service start')
                if parts[0] == 'class_start' and parts[1] not in {'core', 'main', 'late_start'}:
                    raise ValueError('Unexpected service class')
            if parts[0] == 'mount' and parts[1] not in {'rootfs', 'tmpfs', 'cgroup'}:
                raise ValueError('Nonvirtual mount in original init actions')
            if parts[0] == 'copy' and parts[1:] != ['/data/system/entropy.dat', '/dev/urandom']:
                raise ValueError('Unreviewed init copy')
            if parts[0] == 'write' and not parts[1].startswith(('/proc/', '/sys/', '/dev/cpuctl/')):
                raise ValueError('Unreviewed init write')
            output.append('    ' + command)
        output.append('')
    if kept != SERVICES - {'sdcard'}:
        raise ValueError('Original init lacks required service definitions')
    output.extend(['# Record requests; do not shut down/reboot this experiment automatically.',
                   'on property:sys.powerctl=*',
                   '    write /run/android44-powerctl.txt ${sys.powerctl}', ''])
    return '\n'.join(output).encode(), log_uids


def board_init(log_uids):
    # These storage paths reproduce only the RAM-backed emulated storage layout.
    lines = ['# Generated RAM-data board setup; no legacy device/USB imports.', 'on init',
             # Original Android init has already replaced bootstrap /dev here.
             # EventHub fatally requires this watch directory, even with no devices.
             '    mkdir /dev/input 0755 root input',
             '    mkdir /run/android-logs 0755 root root']
    for name, (user, _) in sorted(log_uids.items()):
        lines.append(f'    mkdir /run/android-logs/{name} 0700 {user} root')
    lines.extend(['    mkdir /run/android-logs/sdcard 0700 root root',
                  '    mkdir /mnt/shell/emulated 0700 shell shell',
                  '    mkdir /storage/emulated 0555 root root',
                  '    export EXTERNAL_STORAGE /storage/emulated/legacy',
                  '    export EMULATED_STORAGE_SOURCE /mnt/shell/emulated',
                  '    export EMULATED_STORAGE_TARGET /storage/emulated',
                  '    symlink /storage/emulated/legacy /sdcard',
                  '    symlink /storage/emulated/legacy /mnt/sdcard',
                  '    symlink /storage/emulated/legacy /storage/sdcard0',
                  '    symlink /storage/emulated/legacy /storage/emulated/0',
                  '    symlink /mnt/shell/emulated/0 /storage/emulated/legacy', '',
                  'on fs', '    setprop ro.crypto.fuse_sdcard true', '',
                  'on post-fs-data', '    mkdir /data/media 0775 media_rw media_rw',
                  '    setprop vold.post_fs_data_done 1',
                  '    trigger nonencrypted', '',
                  'service sdcard /bin/android-service-runner sdcard /system/bin/sdcard /data/media /mnt/shell/emulated 1023 1023',
                  '    class late_start', ''])
    return '\n'.join(lines).encode()


def default_properties(original):
    props = {}
    for line in original.decode().splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            props[key] = value
    props.update({'ro.hardware': 'stingray', 'ro.kernel.qemu': '0',
                  'ro.kernel.qemu.gles': '0', 'ro.config.low_ram': 'true',
                  'persist.sys.usb.config': 'none', 'sys.usb.config': 'none',
                  'debug.sf.no_hw_vsync': '1', 'debug.sf.nobootanimation': '1'})
    return ('# Generated experimental RAM-data properties\n' +
            ''.join(f'{key}={value}\n' for key, value in sorted(props.items()))).encode()


def ramdisk_entries(original, files, persistent=False):
    """Copy only the required baseline files, then add generated/runtime files."""
    entries = {}
    for name in ('.', 'data', 'dev', 'proc', 'sys', 'system', 'sbin',
                 'init', 'init.environ.rc', 'ueventd.rc', 'ueventd.stingray.rc',
                 'file_contexts', 'property_contexts', 'sepolicy', 'seapp_contexts', 'sbin/healthd'):
        if name not in original:
            raise ValueError('Required original ramdisk member missing: ' + name)
        entry = original[name]
        if name == 'init':
            entry = replace(entry, name='init.android')
        elif stat.S_ISDIR(entry.mode):
            entry = replace(entry, mode=stat.S_IFDIR | (0o771 if name == 'data' else 0o755))
        entries[entry.name] = entry
    for name in ('bin', 'cache', 'run', 'tmp'):
        entries[name] = Entry(name, stat.S_IFDIR | (0o1777 if name == 'tmp' else 0o755))
    for name, target in {'bin/sh': 'busybox', 'sbin/ueventd': '/init.android',
                         'sbin/watchdogd': '/init.android', 'vendor': '/system/vendor'}.items():
        entries[name] = Entry(name, stat.S_IFLNK | 0o777, target.encode())
    rc, log_uids = transform_init(original['init.rc'].data.decode())
    if persistent:
        fstab = (b'/dev/block/mmcblk0p8 /system ext4 ro,noload,nosuid,nodev wait\n'
                 b'/dev/block/mmcblk0p10 /data ext4 rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic wait\n'
                 b'/dev/block/mmcblk0p9 /cache ext4 rw,noatime,nosuid,nodev,nomblk_io_submit,errors=panic wait\n')
    else:
        fstab = b'/dev/block/mmcblk0p8 /system ext4 ro,noload,nosuid,nodev wait\n'
    generated = {'init.rc': rc, 'init.xoom-firstboot.rc': board_init(log_uids),
                 'default.prop': default_properties(original['default.prop'].data),
                 'fstab.stingray': fstab}
    for name, data in generated.items():
        entries[name] = Entry(name, stat.S_IFREG | 0o644, data)
    for name, data in files.items():
        if name in entries or name.startswith(('/', '../')) or '..' in PurePosixPath(name).parts:
            raise ValueError('Runtime file collision or unsafe path')
        entries[name] = Entry(name, stat.S_IFREG | 0o755, data)
    entries['dev/console'] = Entry('dev/console', stat.S_IFCHR | 0o600, major=5, minor=1)
    entries['dev/null'] = Entry('dev/null', stat.S_IFCHR | 0o666, major=1, minor=3)
    # Round-trip validation catches duplicate/corrupt paths before image output.
    if parse_newc(pack_newc(entries)) != entries:
        raise ValueError('Ramdisk round-trip mismatch')
    return entries


def boot_image(kernel, compressed_ramdisk):
    page, ka, ra, tags = 2048, 0x10008000, 0x11000000, 0x10000100
    if not 48 < len(kernel) < ra - ka:
        raise ValueError('Invalid kernel component length')
    if struct.unpack_from('<I', kernel, 36)[0] != 0x016f2818:
        raise ValueError('Not an ARM zImage')
    header = bytearray(page)
    header[:8] = b'ANDROID!'
    struct.pack_into('<10I', header, 8, len(kernel), ka, len(compressed_ramdisk), ra,
                     0, 0x10f00000, tags, page, 0, 0)
    header[48:59] = b'wingray-a44'
    cmd = (b'androidboot.carrier=wifi-only product_type=w androidboot.hardware=stingray '
           b'androidboot.mode=normal androidboot.selinux=disabled rdinit=/init panic=0 drm.debug=0x06')
    if len(cmd) >= 512:
        raise ValueError('Command line too long')
    header[64:64 + len(cmd)] = cmd
    checksum = hashlib.sha1()
    for component in (kernel, compressed_ramdisk, b''):
        checksum.update(component)
        checksum.update(struct.pack('<I', len(component)))
    header[576:596] = checksum.digest()
    def padded(data):
        return data + b'\0' * (-len(data) % page)
    image = bytes(header) + padded(kernel) + padded(compressed_ramdisk)
    if len(image) > 8 * 1024 * 1024:
        raise ValueError('Image exceeds preserved 8MiB boot partition')
    return image
