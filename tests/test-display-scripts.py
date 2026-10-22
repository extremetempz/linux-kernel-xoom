#!/usr/bin/env python3
"""Run real startup/report scripts with mocked sysfs and a harmless pattern."""
from pathlib import Path
import os,subprocess,tempfile,unittest
root=Path(__file__).resolve().parents[1]
class Display(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='xoom-display-script-');self.p=Path(self.temp.name)
  self.sys=self.p/'sys';self.run=self.p/'run';self.run.mkdir()
  comp=self.sys/'firmware/devicetree/base/compatible';comp.parent.mkdir(parents=True);comp.write_bytes(b'motorola,wingray\0nvidia,tegra20\0');self.compatible=comp
  self.calls=self.p/'calls';self.pattern=self.p/'pattern'
  self.pattern.write_text('#!/bin/sh\necho pattern >> "$TEST_CALLS"\necho XOOM_PATTERN_WRITTEN_MOCK\nexit "${TEST_EXIT:-0}"\n');self.pattern.chmod(0o755)
  self.bb=self.p/'busybox';self.bb.write_text('''#!/bin/sh
case "$1" in
 uname) echo "${TEST_RELEASE:-4.4.147-wingray-display}";exit 0;;
 sleep) echo sleep >> "$TEST_CALLS";exit 0;;
 i2cget|i2cset|devmem|mount) echo FORBIDDEN >> "$TEST_CALLS";exit 99;;
esac
exec /usr/bin/busybox "$@"
''');self.bb.chmod(0o755)
 def tearDown(self):self.temp.cleanup()
 def execute(self,name,device='/dev/null',**env):
  s=(root/f'diagnostic/display-{name}.sh').read_text().replace('/bin/busybox',str(self.bb)).replace('/sys/',str(self.sys)+'/').replace('/run/',str(self.run)+'/').replace('/bin/display-pattern',str(self.pattern)).replace('/dev/fb0',device).replace('/proc/fb',str(self.p/'proc-fb'))
  script=self.p/name;script.write_text(s)
  return subprocess.run(['/usr/bin/busybox','sh',str(script)],env={**os.environ,'TEST_CALLS':str(self.calls),**env},capture_output=True,timeout=3,check=True).stdout
 def test_start_once_and_exit_record(self):
  data=self.execute('start',TEST_EXIT='3');self.assertIn(b'XOOM_PATTERN_EXIT 3',data);self.assertEqual(self.calls.read_text(),'pattern\n')
 def test_wrong_release_denied(self):
  self.assertIn(b'DENIED_RELEASE',self.execute('start',TEST_RELEASE='2.6.39.4'));self.assertFalse(self.calls.exists())
 def test_wrong_board_denied(self):
  self.compatible.write_bytes(b'other\0');self.assertIn(b'DENIED_BOARD',self.execute('start'));self.assertFalse(self.calls.exists())
 def test_missing_fb_bounded(self):
  self.assertIn(b'NO_FB0',self.execute('start',device=str(self.p/'missing')));self.assertEqual(self.calls.read_text().splitlines(),['sleep']*15)
 def test_report_uses_bound_driver_no_bus_commands(self):
  (self.p/'proc-fb').write_text('0 mockfb\n');(self.run/'display-pattern-result.txt').write_text('XOOM_PATTERN_WRITTEN_MOCK\n')
  device=self.sys/'bus/i2c/devices/0-002c';device.mkdir(parents=True);(device/'driver').symlink_to(self.p);(device/'wingray_registers').write_text('0xa0 0x5c\n0x01 0x03\n')
  bl=self.sys/'class/backlight/lcd-backlight';bl.mkdir(parents=True);(bl/'brightness').write_text('128\n')
  data=self.execute('report');self.assertIn(b'0xa0 0x5c',data);self.assertIn(b'brightness=128',data);self.assertIn(b'XOOM_PATTERN_WRITTEN_MOCK',data);self.assertFalse(self.calls.exists())
if __name__=='__main__':unittest.main(verbosity=2)
