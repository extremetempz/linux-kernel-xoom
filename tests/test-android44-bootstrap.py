#!/usr/bin/env python3
"""Exercise actual bootstrap failure gates using ordinary temporary files only."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = [(51200, 6144), (57344, 4096), (61440, 4096), (65536, 8192),
            (73728, 4096), (77824, 24576), (102400, 16384), (118784, 2097152),
            (2215936, 1048576), (3264512, 59247616)]


class Bootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xoom-android44-bootstrap-')
        self.path = Path(self.temp.name)
        for directory in ('sys', 'run', 'dev', 'system/lib/hw', 'system/lib/egl'):
            (self.path / directory).mkdir(parents=True, exist_ok=True)
        compatible = self.path / 'sys/firmware/devicetree/base/compatible'
        compatible.parent.mkdir(parents=True)
        compatible.write_bytes(b'motorola,wingray\0nvidia,tegra20\0')
        disk = self.path / 'sys/block/mmcblk0'
        disk.mkdir(parents=True)
        (disk / 'size').write_text('62521344\n')
        (disk / 'ro').write_text('1\n')
        for i, (start, size) in enumerate(GEOMETRY, 1):
            part = disk / f'mmcblk0p{i}'
            part.mkdir()
            for name, value in (('start', start), ('size', size), ('ro', 1)):
                (part / name).write_text(f'{value}\n')
        (self.path / 'dev/fb0').touch()
        for name in ('gralloc.default', 'audio.primary.default', 'audio_policy.default',
                     'power.default', 'keystore.default', 'local_time.default'):
            (self.path / f'system/lib/hw/{name}.so').write_text('fixture, never executed')
        (self.path / 'system/lib/egl/libGLES_android.so').write_text('fixture, never executed')
        self.bb = self.path / 'busybox'
        self.bb.write_text('''#!/bin/sh
case "$1" in
 uname) echo "${MOCK_RELEASE:-4.4.147-wingray-android44}"; exit 0 ;;
 mount) echo "mount $*" >> "$MOCK_CALLS"; exit "${MOCK_MOUNT_EXIT:-0}" ;;
 sha256sum) echo checksum >> "$MOCK_CALLS"; exit "${MOCK_HASH_EXIT:-0}" ;;
 sleep) echo sleep >> "$MOCK_CALLS"; exit 0 ;;
esac
exec /usr/bin/busybox "$@"
''')
        self.bb.chmod(0o755)
        for name, value in [('abi', 'MOCK_ABI_EXIT'), ('pattern', 'MOCK_PATTERN_EXIT')]:
            p = self.path / name
            p.write_text(f'#!/bin/sh\necho {name} >> "$MOCK_CALLS"\nexit "${{{value}:-0}}"\n')
            p.chmod(0o755)
        p = self.path / 'original-init'
        p.write_text('#!/bin/sh\necho original-init >> "$MOCK_CALLS"\n')
        p.chmod(0o755)

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, **extra):
        source = (ROOT / 'diagnostic/android44-bootstrap.sh').read_text()
        # Replace only the terminal wait in fail(), so a denial is observable.
        source = source.replace('while :; do /bin/busybox sleep 5; done', 'exit 88')
        for old, new in (('/bin/android44-abi-probe', str(self.path / 'abi')),
                         ('/bin/display-pattern', str(self.path / 'pattern')),
                         ('/init.android', str(self.path / 'original-init')),
                         ('/bin/busybox', str(self.bb))):
            source = source.replace(old, new)
        source = re.sub(r'(?<![\w/])/(?:sys|run|dev|system|vendor|data|cache)(?=/|\s|$)',
                        lambda match: str(self.path) + match[0], source)
        script = self.path / 'bootstrap'
        script.write_text(source)
        calls = self.path / 'calls'
        result = subprocess.run(['/usr/bin/busybox', 'sh', str(script)],
                                env={**os.environ, 'MOCK_CALLS': str(calls), **extra},
                                capture_output=True, timeout=3)
        self.calls = calls.read_text().splitlines() if calls.exists() else []
        self.stages = (self.path / 'run/android44-stages.txt').read_text()
        return result

    def test_success_only_mounts_fixed_ro_system_and_ram_then_execs(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        mounts = [line for line in self.calls if line.startswith('mount ')]
        block_mounts = [line for line in mounts if 'mmcblk0' in line]
        self.assertEqual(len(block_mounts), 1)
        self.assertIn('ro,noload,nosuid,nodev', block_mounts[0])
        self.assertIn('/dev/mmcblk0p8', block_mounts[0])
        self.assertEqual(self.calls[-1], 'original-init')
        self.assertIn('exec_original_android_init', self.stages)
        self.assertEqual((self.path / 'run/xoom-egl/libGLES.so').read_text(), 'fixture, never executed')

    def test_wrong_release_or_any_partition_ro_denies_before_abi_or_mounts(self):
        result = self.execute(MOCK_RELEASE='2.6.39.4')
        self.assertEqual(result.returncode, 88)
        self.assertEqual(self.calls, [])
        for i in range(1, 11):
            with self.subTest(partition=i):
                p = self.path / f'sys/block/mmcblk0/mmcblk0p{i}/ro'
                p.write_text('0\n')
                result = self.execute()
                self.assertEqual(result.returncode, 88)
                self.assertEqual(self.calls, [])
                p.write_text('1\n')

    def test_capacity_and_geometry_denials_before_mounts(self):
        p = self.path / 'sys/block/mmcblk0/size'
        p.write_text('1\n')
        self.assertEqual(self.execute().returncode, 88)
        self.assertEqual(self.calls, [])
        p.write_text('62521344\n')
        p = self.path / 'sys/block/mmcblk0/mmcblk0p8/start'
        p.write_text('0\n')
        self.assertEqual(self.execute().returncode, 88)
        self.assertEqual(self.calls, [])

    def test_abi_failure_stops_before_display_or_mounts(self):
        self.assertEqual(self.execute(MOCK_ABI_EXIT='14').returncode, 88)
        self.assertEqual(self.calls, ['abi'])
        self.assertIn('FAILED_abi', self.stages)

    def test_no_display_failure_is_bounded_and_stops_before_mounts(self):
        (self.path / 'dev/fb0').unlink()
        self.assertEqual(self.execute(MOCK_PATTERN_EXIT='1').returncode, 88)
        self.assertEqual(self.calls.count('sleep'), 15)
        self.assertFalse(any(line.startswith('mount ') for line in self.calls))
        self.assertIn('FAILED_display', self.stages)

    def test_mount_hash_or_vendor_failure_never_execs_android(self):
        self.assertEqual(self.execute(MOCK_MOUNT_EXIT='1').returncode, 88)
        self.assertNotIn('original-init', self.calls)
        # Clear prior invocation log so the next checks are independent.
        (self.path / 'calls').unlink()
        self.assertEqual(self.execute(MOCK_HASH_EXIT='1').returncode, 88)
        self.assertFalse(any('bind' in line for line in self.calls))
        self.assertNotIn('original-init', self.calls)
        (self.path / 'calls').unlink()
        (self.path / 'system/vendor/lib/hw').mkdir(parents=True)
        self.assertEqual(self.execute().returncode, 88)
        self.assertIn('FAILED_vendor_layout', self.stages)
        self.assertNotIn('original-init', self.calls)


if __name__ == '__main__':
    unittest.main()
