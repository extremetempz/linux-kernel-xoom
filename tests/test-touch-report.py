#!/usr/bin/env python3
"""Run actual fixed read-only shell report against private fake sysfs/proc.
No device accesses or touch-state changes. Worst-case test includes the native
reader's separately asserted upper bound, not only its common short output.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class TouchReport(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='xoom-touch-report-')
  self.p=Path(self.temp.name);self.sys=self.p/'sys';self.proc=self.p/'proc'
  self.calls=self.p/'calls';self.reader=self.p/'touch-events'
  self.reader.write_text('#!/bin/sh\necho native_sample >> "$TEST_CALLS"\necho XOOM_TOUCH_EVENTS_BEGIN\necho XOOM_TOUCH_SAMPLE_STATUS deadline_complete\necho XOOM_TOUCH_EVENTS_END\nexit "${TEST_EXIT:-0}"\n');self.reader.chmod(0o755)
  self.bb=self.p/'busybox'
  self.bb.write_text('''#!/bin/sh
case "$1" in
 uname) echo "${TEST_RELEASE:-4.4.147-wingray-android44-touch}";exit 0;;
 i2cget|i2cset|i2cdetect|devmem|mount|insmod|modprobe|chmod|chown)
  echo FORBIDDEN >> "$TEST_CALLS";exit 99;;
esac
exec /usr/bin/busybox "$@"
''');self.bb.chmod(0o755)
  self.compatible=self.sys/'firmware/devicetree/base/compatible'
  self.compatible.parent.mkdir(parents=True)
  self.compatible.write_bytes(b'motorola,wingray\0nvidia,tegra20\0')
  i2c=self.sys/'bus/i2c/devices/0-005b';i2c.mkdir(parents=True)
  (i2c/'driver').symlink_to('/sys/bus/i2c/drivers/atmel_mxt_ts')
  for name,value in [('name','atmel_mxt_ts'),('modalias','i2c:atmel_mxt_ts'),('fw_version','2.1.09'),('hw_version','128.1')]:
   (i2c/name).write_text(value+'\n')
  (self.proc/'bus/input').mkdir(parents=True)
  (self.proc/'bus/input/devices').write_text('N: Name="Atmel maXTouch Touchscreen"\n')
  (self.proc/'interrupts').write_text('250: 125 mxttouch\n')
 def tearDown(self):self.temp.cleanup()
 def device(self,index,name='Atmel maXTouch Touchscreen',length=12):
  path=self.sys/f'class/input/event{index}/device'
  path.mkdir(parents=True)
  for attr in ['name','phys','properties','capabilities/ev','capabilities/key','capabilities/abs']:
   target=path/attr;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_text(name+'\n' if attr=='name' else 'A'*length)
  return path
 def execute(self,**env):
  script=(ROOT/'diagnostic/touch-report.sh').read_text().replace('/bin/busybox',str(self.bb)).replace('/bin/touch-events',str(self.reader)).replace('/sys/',str(self.sys)+'/').replace('/proc/',str(self.proc)+'/')
  target=self.p/'report.sh';target.write_text(script)
  result=subprocess.run(['/usr/bin/busybox','sh',str(target)],env={**os.environ,'TEST_CALLS':str(self.calls),**env},capture_output=True,timeout=3,check=True)
  self.assertNotIn(b'FORBIDDEN',self.calls.read_bytes() if self.calls.exists() else b'')
  return result.stdout+result.stderr
 def test_fixed_metadata_and_sample(self):
  self.device(3)
  data=self.execute(TEST_EXIT='3')
  self.assertIn(b'XOOM_TOUCH_I2C fw_version\n2.1.09',data)
  self.assertIn(b'XOOM_TOUCH_INPUT event3',data)
  self.assertIn(b'XOOM_TOUCH_SAMPLE_EXIT 3',data)
  self.assertEqual(self.calls.read_text(),'native_sample\n')
  self.assertEqual(data.count(b'250: 125 mxttouch'),2)
 def test_release_denied_before_metadata_or_reader(self):
  data=self.execute(TEST_RELEASE='4.4.147-wingray-android44')
  self.assertIn(b'XOOM_TOUCH_DENIED_RELEASE',data)
  self.assertNotIn(b'XOOM_TOUCH_I2C_METADATA_BEGIN',data)
  self.assertFalse(self.calls.exists())
 def test_wrong_board_denied(self):
  self.compatible.write_bytes(b'motorola,wingray-other\0')
  data=self.execute();self.assertIn(b'XOOM_TOUCH_DENIED_BOARD',data)
  self.assertFalse(self.calls.exists())
 def test_missing_reader_reported(self):
  self.reader.unlink();data=self.execute()
  self.assertIn(b'XOOM_TOUCH_SAMPLE_MISSING',data);self.assertFalse(self.calls.exists())
 def test_exact_name_first_only_and_event_whitelist(self):
  self.device(0,name='Atmel maXTouch Touchpad')
  self.device(15);self.device(16)
  data=self.execute()
  self.assertIn(b'XOOM_TOUCH_INPUT event15\n',data)
  self.assertNotIn(b'XOOM_TOUCH_INPUT event0\n',data)
  self.assertNotIn(b'XOOM_TOUCH_INPUT event16\n',data)
 def test_adversarial_report_with_native_upper_bound_under_24k(self):
  for index in range(16):self.device(index,length=20000)
  for name in ['name','modalias','fw_version','hw_version']:
   (self.sys/'bus/i2c/devices/0-005b'/name).write_bytes(b'I'*20000)
  (self.proc/'bus/input/devices').write_bytes(b'P'*20000)
  (self.proc/'interrupts').write_bytes(b'Q'*20000)
  self.reader.write_text('#!/bin/sh\necho native_sample >> "$TEST_CALLS"\n/usr/bin/busybox head -c 8191 /dev/zero | /usr/bin/busybox tr "\\000" N\n')
  data=self.execute()
  self.assertEqual(data.count(b'XOOM_TOUCH_INPUT event'),1)
  self.assertIn(b'N'*8191,data)
  self.assertLess(len(data),24*1024)
  print(f'Adversarial full touch report: {len(data)} bytes (<24576), including 8191-byte native upper bound.')
 def test_source_avoids_object_or_raw_bus_access(self):
  source=(ROOT/'diagnostic/touch-report.sh').read_text()
  for forbidden in ['i2cget','i2cset','i2cdetect','/object','/update_fw','/mem_access','/dev/mem']:
   self.assertNotIn(forbidden,source)
if __name__=='__main__':unittest.main(verbosity=2)
