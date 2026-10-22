#!/usr/bin/env python3
"""Offline archive, startup and boot-header regression checks; no device access."""
import gzip
import hashlib
from pathlib import Path
import stat
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from android44_image import (Entry, SERVICES, board_init, boot_image, default_properties,
                             original_entries, pack_newc, parse_newc, ramdisk_entries,
                             sections, transform_init)


def fixture_init():
    rc = '''import /init.usb.rc
on early-init
    start ueventd
on init
    mount cgroup none /acct cpuacct
    mount tmpfs none /sys/fs/cgroup mode=0750,uid=0,gid=1000
    mount cgroup none /sys/fs/cgroup/memory memory
on post-fs
    mount rootfs rootfs / ro remount
on post-fs-data
    mkdir /data/system 0775 system system
    import /init.eos.rc
on boot
    class_start core
    class_start main
on nonencrypted
    class_start late_start
on property:persist.sys.recovery_update=true
    start flash_recovery
service flash_recovery /system/etc/install-cm-recovery.sh
    class main
service modem /system/bin/tty2ttyd /dev/ttyGS0
    class main
'''
    users = {'surfaceflinger': 'system', 'servicemanager': 'system',
             'drm': 'drm', 'media': 'media', 'keystore': 'keystore'}
    for name in sorted(SERVICES - {'sdcard'}):
        path = '/sbin/' + name if name in {'ueventd', 'healthd'} else '/system/bin/' + name
        rc += f'service {name} {path}\n    class main\n    critical\n'
        if name in users:
            rc += f'    user {users[name]}\n'
        if name == 'zygote':
            rc += '    socket zygote stream 660 root system\n'
            rc += '    onrestart write /sys/power/state on\n'
    return rc


class ArchiveTests(unittest.TestCase):
    def test_roundtrip_preserves_metadata_without_following_links(self):
        entries = {
            '.': Entry('.', stat.S_IFDIR | 0o755),
            'init.android': Entry('init.android', stat.S_IFREG | 0o750, b'original\0binary'),
            'sbin': Entry('sbin', stat.S_IFDIR | 0o755),
            'sbin/ueventd': Entry('sbin/ueventd', stat.S_IFLNK | 0o777, b'/init.android'),
            'dev/console': Entry('dev/console', stat.S_IFCHR | 0o600, major=5, minor=1),
            'data': Entry('data', stat.S_IFDIR | 0o771, uid=1000, gid=1000),
        }
        self.assertEqual(parse_newc(pack_newc(entries)), entries)

    def test_rejects_truncation_paths_duplicates_hardlinks_and_second_archive(self):
        good = pack_newc({'a': Entry('a', stat.S_IFREG | 0o644, b'x')})
        invalid = [good[:100], good[:113], good[:120], good + good]
        for name in ('../boot', '/init', 'foo//bar', 'foo/./bar'):
            invalid.append(pack_newc({name: Entry(name, stat.S_IFREG | 0o644)}))
        # Duplicate the first record before the legitimate trailer.
        record_end = (112 + 1 + 3) & ~3
        invalid.append(good[:record_end] + good)
        hardlink = bytearray(good)
        hardlink[38:46] = b'00000002'
        invalid.append(bytes(hardlink))
        for data in invalid:
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                parse_newc(data)

    def test_original_hash_pin_rejects_unknown_input_before_unpacking(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            original_entries(b'ANDROID!' + b'\0' * 4096)


class StartupTests(unittest.TestCase):
    def test_discards_all_legacy_imports_and_services(self):
        rc, uids = transform_init(fixture_init())
        text = rc.decode()
        self.assertEqual([line for line in text.splitlines() if line.startswith('import ')],
                         ['import /init.environ.rc', 'import /init.xoom-firstboot.rc'])
        for excluded in ('ttyGS', 'flash_recovery', 'critical', 'eos.rc', 'usb.rc',
                         '/sys/power/state', '/sys/fs/cgroup/memory'):
            self.assertNotIn(excluded, text)
        self.assertIn('service ueventd /sbin/ueventd', text)
        self.assertIn('service surfaceflinger /bin/android-service-runner surfaceflinger /system/bin/surfaceflinger', text)
        self.assertIn('socket zygote stream 660 root system', text)
        self.assertEqual(uids['surfaceflinger'], ('system', 1000))
        board = board_init(uids).decode()
        self.assertIn('mkdir /run/android-logs/surfaceflinger 0700 system root', board)
        self.assertIn('trigger nonencrypted', board)
        self.assertNotIn('mount_all', board)

    def test_unreviewed_mutations_and_unknown_service_uids_fail_closed(self):
        for line in ('mount ext4 /dev/mmcblk0p10 /data rw', 'exec /system/bin/mkfs',
                     'write /dev/mmcblk0p7 corrupt', 'start flash_recovery',
                     'copy /system/file /dev/block/mmcblk0p6'):
            rc = fixture_init().replace('    class_start core', '    ' + line)
            with self.subTest(line=line), self.assertRaises(ValueError):
                transform_init(rc)
        with self.assertRaisesRegex(ValueError, 'UID'):
            transform_init(fixture_init().replace('user system', 'user unknown'))

    def test_software_graphics_defaults_do_not_claim_qemu_hardware(self):
        props = default_properties(b'ro.kernel.qemu=1\nro.debuggable=1\n').decode()
        self.assertIn('ro.kernel.qemu=0\n', props)
        self.assertIn('ro.kernel.qemu.gles=0\n', props)
        self.assertIn('persist.sys.usb.config=none\n', props)


class HeaderTests(unittest.TestCase):
    def test_v0_layout_id_cmdline_and_limit(self):
        kernel = bytearray(2048)
        struct.pack_into('<I', kernel, 36, 0x016f2818)
        ramdisk = gzip.compress(b'test archive', mtime=0)
        image = boot_image(bytes(kernel), ramdisk)
        ks, ka, rs, ra, second, _, tags, page = struct.unpack_from('<8I', image, 8)
        self.assertEqual((ks, ka, rs, ra, second, tags, page),
                         (2048, 0x10008000, len(ramdisk), 0x11000000, 0, 0x10000100, 2048))
        cmd = image[64:576].split(b'\0')[0]
        self.assertIn(b'androidboot.hardware=stingray', cmd)
        self.assertIn(b'androidboot.mode=normal', cmd)
        self.assertIn(b'rdinit=/init', cmd)
        sha = hashlib.sha1()
        for component in (bytes(kernel), ramdisk, b''):
            sha.update(component)
            sha.update(struct.pack('<I', len(component)))
        self.assertEqual(image[576:596], sha.digest())
        self.assertEqual(image[4096:4096 + rs], ramdisk)
        with self.assertRaisesRegex(ValueError, '8MiB'):
            boot_image(bytes(kernel), b'x' * (8 * 1024 * 1024))


class PrivateIntegrationTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'artifacts/hardware-private/backup-boot.img').is_file(),
                         'Private preserved boot image is not available')
    def test_actual_preserved_archive_transforms_without_modifying_original(self):
        path = ROOT / 'artifacts/hardware-private/backup-boot.img'
        before = path.read_bytes()
        original = original_entries(before)
        transformed = ramdisk_entries(original, {'init': b'#!/bin/busybox sh\n'})
        self.assertEqual(transformed['init.android'].data, original['init'].data)
        self.assertEqual(transformed['sbin/ueventd'].data, b'/init.android')
        self.assertEqual(transformed['sbin/watchdogd'].data, b'/init.android')
        self.assertNotIn('init.eos.rc', transformed)
        self.assertNotIn('sbin/adbd', transformed)
        self.assertNotIn('init.stingray.usb.rc', transformed)
        self.assertNotIn('mount_all', transformed['init.rc'].data.decode())
        self.assertIn(b'BOOTCLASSPATH', transformed['init.environ.rc'].data)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
