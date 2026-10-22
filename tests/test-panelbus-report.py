#!/usr/bin/env python3
"""Run actual readiness script with mocked kernel metadata and I2C applet.

Never opens a real I2C bus. /dev/null supplies the character-device type check.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

root=Path(__file__).resolve().parents[1]
REGS=['0x00','0x01','0x03','0x04',*[f'0xa{i}' for i in range(8)]]

class PanelBus(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='xoom-panelbus-');self.p=Path(self.temp.name)
  self.sys=self.p/'sys';self.run=self.p/'run';self.run.mkdir()
  self.node=self.sys/'firmware/devicetree/base/i2c@7000c000';self.node.mkdir(parents=True)
  self.compatible=self.node.parent/'compatible';self.compatible.write_bytes(b'motorola,wingray\0nvidia,tegra20\0')
  adapter=self.sys/'class/i2c-adapter/i2c-0';adapter.mkdir(parents=True);(adapter/'of_node').symlink_to(self.node)
  self.adapter=adapter
  self.calls=self.p/'calls'
  bb=self.p/'busybox';bb.write_text('''#!/bin/sh
case "$1" in
 uname) echo "${TEST_RELEASE:-4.4.147-wingray-panelbus}"; exit 0;;
 i2cget)
  echo "$*" >> "$TEST_CALLS"
  [ "$5" != "$TEST_FAIL_REG" ] || exit 1
  echo 0xfc; exit 0;;
esac
exec /usr/bin/busybox "$@"
''');bb.chmod(0o755)
  self.source=(root/'diagnostic/panelbus-report.sh').read_text().replace('/bin/busybox',str(bb)).replace('/sys/',str(self.sys)+'/').replace('/run/',str(self.run)+'/').replace('/dev/i2c-0','/dev/null')
 def tearDown(self):self.temp.cleanup()
 def execute(self,**env):
  script=self.p/'report';script.write_text(self.source)
  result=subprocess.run(['/usr/bin/busybox','sh',str(script)],env={**os.environ,'TEST_CALLS':str(self.calls),'TEST_FAIL_REG':'',**env},capture_output=True,timeout=3,check=True)
  self.assertEqual(result.stderr,b'');return result.stdout
 def test_fixed_reads_and_success(self):
  data=self.execute();self.assertIn(b'XOOM_PANELBUS_STATUS read_complete\n',data)
  self.assertEqual(self.calls.read_text().splitlines(),[f'i2cget -y 0 0x2c {r} b' for r in REGS])
  self.assertEqual(data.count(b'XOOM_LP8550_REG '),12)
 def test_stops_on_first_error(self):
  data=self.execute(TEST_FAIL_REG='0xa0')
  self.assertIn(b'XOOM_PANELBUS_READ_ERROR 0xa0 1\n',data);self.assertIn(b'XOOM_PANELBUS_STATUS read_failed\n',data)
  self.assertEqual(len(self.calls.read_text().splitlines()),5)
 def test_release_gate(self):
  self.assertIn(b'denied_release',self.execute(TEST_RELEASE='4.4.147-wingray-diagnostic'));self.assertFalse(self.calls.exists())
 def test_board_gate(self):
  self.compatible.write_bytes(b'nvidia,other\0');self.assertIn(b'denied_board',self.execute());self.assertFalse(self.calls.exists())
 def test_adapter_gate(self):
  (self.adapter/'of_node').unlink();(self.adapter/'of_node').symlink_to(self.node.parent/'i2c@other')
  self.assertIn(b'denied_adapter',self.execute());self.assertFalse(self.calls.exists())
 def test_device_gate(self):
  plain=self.p/'plain';plain.touch();self.source=self.source.replace('/dev/null',str(plain))
  self.assertIn(b'missing_device',self.execute());self.assertFalse(self.calls.exists())

if __name__=='__main__':unittest.main(verbosity=2)
