#!/usr/bin/env python3
"""Run the actual fixed Android reporter against harmless host-only metadata."""
from pathlib import Path
import os
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AndroidReport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='xoom-android-report-')
        self.path = Path(self.temp.name)
        for name in ('proc/self', 'run', 'sys', 'dev', 'system/bin', 'data/tombstones'):
            (self.path/name).mkdir(parents=True)
        self.compatible = self.path/'sys/firmware/devicetree/base/compatible'
        self.compatible.parent.mkdir(parents=True)
        self.compatible.write_bytes(b'motorola,wingray\0nvidia,tegra20\0')
        disk = self.path/'sys/block/mmcblk0'
        disk.mkdir(parents=True)
        (disk/'ro').write_text('1\n')
        for number in range(1, 11):
            part = disk/f'mmcblk0p{number}'
            part.mkdir()
            (part/'ro').write_text('1\n')
        (self.path/'proc/self/mountinfo').write_text('10 1 0:5 / /run rw - tmpfs tmpfs rw\n')
        (self.path/'proc/meminfo').write_text('MemTotal: 1024000 kB\nMemFree: 512000 kB\n')
        self.mounts = self.path/'proc/mounts'
        self.mounts.write_text('tmpfs /run tmpfs rw 0 0\n'
                               'tmpfs /data tmpfs rw 0 0\n'
                               '/dev/mmcblk0p8 /system ext4 ro,nosuid,nodev,norecovery 0 0\n')
        self.calls = self.path/'calls'
        self.busybox = self.path/'busybox'
        self.busybox.write_text('''#!/bin/sh
case "$1" in
 uname) echo "${TEST_RELEASE:-4.4.147-wingray-android44}"; exit 0;;
 ps) echo 'PID USER COMMAND'; echo '1 root /init.android'; exit 0;;
 timeout) echo "$*" >> "$TEST_CALLS";;
 mount|umount|mknod|dd|devmem|i2cget|i2cset|setprop|chmod|chown|tee)
  echo "FORBIDDEN $*" >> "$TEST_CALLS"; exit 99;;
esac
exec /usr/bin/busybox "$@"
''')
        self.busybox.chmod(0o755)
        self.native('getprop', "printf '[sys.boot_completed]: [1]\\n[init.svc.zygote]: [running]\\n[ro.serialno]: [DO_NOT_REPORT]\\n'")
        self.native('logcat', "printf 'fixture SurfaceFlinger initialized\\n'")

    def tearDown(self):
        self.temp.cleanup()

    def native(self, name, content):
        path = self.path/'system/bin'/name
        path.write_text('#!/bin/sh\n'+content+'\n')
        path.chmod(0o755)

    def execute(self, **env):
        script = (ROOT/'diagnostic/android44-report.sh').read_text()
        script = script.replace('/bin/busybox', str(self.busybox))
        for name in ('proc', 'sys', 'run', 'data', 'dev'):
            script = script.replace('/'+name+'/', str(self.path/name)+'/')
        script = script.replace('/system/bin/', str(self.path/'system/bin')+'/')
        # The expected cmdline remains canonical even though native tools are mocks.
        script = script.replace(str(self.path/'system/bin/sdcard')+'\n', '/system/bin/sdcard\n')
        script = script.replace(str(self.path/'data/media')+'\n', '/data/media\n')
        # Mount-table device names and fixed identity strings stay canonical.
        script = script.replace(str(self.path/'dev/mmcblk0p8'), '/dev/mmcblk0p8')
        target = self.path/'report'
        target.write_text(script)
        result = subprocess.run(['/usr/bin/busybox', 'sh', str(target)],
                                env={**os.environ, 'TEST_CALLS': str(self.calls), **env},
                                capture_output=True, timeout=8, check=True)
        if self.calls.exists():
            self.assertNotIn('FORBIDDEN', self.calls.read_text())
        return result.stdout

    def test_identity_flags_fixed_readonly_properties_and_exit_status(self):
        (self.path/'run/android44-stages.txt').write_text('XOOM_ANDROID44_STAGE abi_passed\n')
        (self.path/'run/android44-abi.txt').write_text('XOOM_ANDROID44_ABI_EXIT 0\n')
        (self.path/'run/android44-powerctl.txt').write_text('shutdown,battery\n')
        result = self.execute()
        self.assertEqual(result.count(b'XOOM_ANDROID44_BLOCK_RO '), 11)
        self.assertIn(b'XOOM_ANDROID44_RELEASE 4.4.147-wingray-android44\n', result)
        self.assertIn(b'XOOM_ANDROID44_BOARD motorola,wingray\n', result)
        self.assertIn(b'XOOM_ANDROID44_STAGE abi_passed', result)
        self.assertIn(b'MemFree: 512000 kB', result)
        self.assertIn(b'shutdown,battery', result)
        self.assertIn(b'[sys.boot_completed]: [1]', result)
        self.assertIn(b'[init.svc.zygote]: [running]', result)
        self.assertNotIn(b'DO_NOT_REPORT', result)
        self.assertIn(b'XOOM_ANDROID44_GETPROP_EXIT 0', result)
        self.assertIn(b'fixture SurfaceFlinger initialized', result)
        self.assertIn(b'XOOM_ANDROID44_LOGCAT_EXIT 0', result)
        self.assertTrue(result.endswith(b'XOOM_ANDROID44_REPORT_DONE_V1\n'))
        calls = self.calls.read_text().splitlines()
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call.startswith('timeout -s KILL 2 ') for call in calls))

    def test_wrong_release_and_wrong_board_do_not_run_native_tools(self):
        self.assertIn(b'DENIED_RELEASE', self.execute(TEST_RELEASE='2.6.39.4'))
        self.assertFalse(self.calls.exists())
        self.compatible.write_bytes(b'nvidia,other\0')
        self.assertIn(b'DENIED_BOARD', self.execute())
        self.assertFalse(self.calls.exists())

    def test_input_directory_presence_is_reported_without_creating_devices(self):
        self.assertIn(b'XOOM_ANDROID44_INPUT_DIRECTORY missing', self.execute())
        (self.path/'dev/input').mkdir()
        self.assertIn(b'XOOM_ANDROID44_INPUT_DIRECTORY present', self.execute())
        self.assertEqual(list((self.path/'dev/input').iterdir()), [])

    def test_missing_readonly_flags_are_explicit(self):
        disk = self.path/'sys/block/mmcblk0'
        (disk/'mmcblk0p9/ro').unlink()
        (disk/'mmcblk0p2/ro').write_text('unexpected\n')
        result = self.execute()
        self.assertIn(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 missing', result)
        self.assertIn(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p2 missing', result)

    def test_mount_gates_prevent_native_and_userdata_reads(self):
        (self.path/'data/tombstones/tombstone_00').write_text('MUST_NOT_READ_OLD_DATA')
        self.mounts.write_text('/dev/mmcblk0p10 /data ext4 ro 0 0\n'
                               '/dev/mmcblk0p8 /system ext4 ro 0 0\n')
        result = self.execute()
        self.assertIn(b'NATIVE_READS_DENIED_MOUNT', result)
        self.assertIn(b'TOMBSTONES_DENIED_DATA', result)
        self.assertNotIn(b'MUST_NOT_READ_OLD_DATA', result)
        self.assertFalse(self.calls.exists())

    def test_service_tombstone_symlinks_and_output_bounds(self):
        service = self.path/'run/android-logs/zygote'
        service.mkdir(parents=True)
        (service/'stdout.txt').write_bytes(b'Z'*100000)
        secret = self.path/'secret'
        secret.write_text('DO_NOT_FOLLOW_SYMLINK')
        (self.path/'data/tombstones/tombstone_00').symlink_to(secret)
        (self.path/'data/tombstones/tombstone_01').write_bytes(b'T'*100000)
        self.native('logcat', f'/usr/bin/busybox head -c 100000 {service/"stdout.txt"}')
        result = self.execute()
        self.assertNotIn(b'DO_NOT_FOLLOW_SYMLINK', result)
        self.assertNotIn(b'Z'*32769, result)
        self.assertNotIn(b'T'*4097, result)
        self.assertLess(len(result), 50000)

    def test_sdcard_requires_exact_bounded_cmdline(self):
        process = self.path/'proc/101'
        process.mkdir()
        (process/'comm').write_text('sdcard\n')
        cmdline = process/'cmdline'
        # Separate byte strings prevent \010 from being interpreted as octal.
        cmdline.write_bytes(b'\0'.join([b'/system/bin/sdcard',b'/data/media',b'/mnt/shell/emulated',b'1023',b'1023'])+b'\0')
        self.assertIn(b'XOOM_ANDROID44_SDCARD_RAM_SOURCE verified', self.execute())
        cmdline.write_bytes(cmdline.read_bytes().replace(b'/data/media', b'/data-old/media'))
        self.assertIn(b'XOOM_ANDROID44_SDCARD_RAM_SOURCE unverified', self.execute())

    def test_native_hang_is_killed_and_completion_marker_survives(self):
        self.native('logcat', 'exec /usr/bin/busybox sleep 20')
        started = time.monotonic()
        result = self.execute()
        self.assertLess(time.monotonic() - started, 6)
        self.assertIn(b'XOOM_ANDROID44_LOGCAT_EXIT 137', result)
        self.assertTrue(result.endswith(b'XOOM_ANDROID44_REPORT_DONE_V1\n'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
