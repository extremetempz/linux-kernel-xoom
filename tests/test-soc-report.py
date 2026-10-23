#!/usr/bin/env python3
"""Execute actual bounded metadata helper on synthetic sysfs/proc; no device."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Report(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='xoom-soc-report-')
        self.p=Path(self.temp.name);self.calls=self.p/'calls'
        self.bb=self.p/'busybox'
        self.bb.write_text('''#!/bin/sh
echo "$1" >> "$TEST_CALLS"
case "$1" in
 uname) echo "${TEST_RELEASE:-4.4.147-wingray-android44-touch}";exit 0;;
 head|tr|grep) exec /usr/bin/busybox "$@";;
 *) echo FORBIDDEN >&2;exit 99;;
esac
''');self.bb.chmod(0o755)
        self.put('sys/firmware/devicetree/base/compatible',b'motorola,wingray\0nvidia,tegra20\0')

    def tearDown(self):self.temp.cleanup()

    def put(self,name,data):
        p=self.p/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)

    def run_report(self,release='4.4.147-wingray-android44-touch'):
        text=(ROOT/'diagnostic/soc-report.sh').read_text().replace('/bin/busybox',str(self.bb))
        text=text.replace('/sys/',str(self.p/'sys')+'/').replace('/proc/',str(self.p/'proc')+'/')
        script=self.p/'soc-report.sh';script.write_text(text)
        result=subprocess.run(['/usr/bin/busybox','sh',str(script)],capture_output=True,timeout=3,
            env={**os.environ,'TEST_CALLS':str(self.calls),'TEST_RELEASE':release})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn(b'FORBIDDEN',result.stderr)
        return result.stdout

    def test_fixed_masks_clocks_memory_and_missing_interfaces(self):
        self.put('sys/devices/system/cpu/online',b'0-1\n')
        self.put('proc/meminfo',b'MemAvailable: 512000 kB\n')
        self.put('sys/module/lowmemorykiller/parameters/adj',b'0,58,117,176,529,1000\n')
        data=self.run_report()
        self.assertIn(b'0-1\n',data);self.assertIn(b'MemAvailable:',data)
        self.assertIn(b'0,58,117,176,529,1000',data)
        self.assertIn(b'unavailable',data);self.assertTrue(data.endswith(b'XOOM_SOC_END\n'))

    def test_exact_new_cpu_profiles_and_unknown_release(self):
        for suffix in ['l2','smp','smp2','smptrace']:
            self.assertNotIn(b'DENIED',self.run_report('4.4.147-wingray-android44-'+suffix))
        self.calls.unlink();data=self.run_report('4.4.147-wingray-android44-smp3')
        self.assertIn(b'DENIED_RELEASE',data);self.assertEqual(self.calls.read_text(),'uname\n')

    def test_wrong_board_denied_before_metadata(self):
        self.put('sys/firmware/devicetree/base/compatible',b'samsung,p4wifi\0')
        data=self.run_report();self.assertIn(b'DENIED_BOARD',data)
        self.assertNotIn('head',self.calls.read_text())

    def test_all_fixed_files_adversarial_under_24k(self):
        names=['proc/cpuinfo','proc/meminfo','proc/vmstat']
        names += ['sys/devices/soc0/'+x for x in ['family','soc_id','revision']]
        names += ['sys/devices/system/cpu/'+x for x in ['possible','present','online','offline']]
        for cpu in range(2):
            names += [f'sys/devices/system/cpu/cpu{cpu}/cpufreq/'+x for x in
                ['scaling_driver','scaling_cur_freq','cpuinfo_cur_freq','scaling_min_freq','scaling_max_freq','scaling_available_frequencies']]
            for index in range(3):
                names += [f'sys/devices/system/cpu/cpu{cpu}/cache/index{index}/'+x for x in
                    ['level','type','size','coherency_line_size','ways_of_associativity']]
        names += ['sys/kernel/debug/clk/'+x+'/clk_rate' for x in ['cclk','pll_x','pll_p','emc']]
        names += ['sys/module/lowmemorykiller/parameters/'+x for x in ['adj','minfree']]
        for name in names:self.put(name,b'A'*25000)
        data=self.run_report();self.assertLess(len(data),24576)
        print('Adversarial CPU/memory metadata bytes:',len(data))


if __name__=='__main__':unittest.main(verbosity=2)
