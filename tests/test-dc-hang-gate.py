#!/usr/bin/env python3
"""Actual manual gate fault checks; no device, clock or IRQ operations."""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1]
s=(R/'sources/kernel-donor/drivers/staging/tegra/video/fb.c').read_text()
a=s.index('static ssize_t wingray_dc_test_store(');b=s.index('\nstatic DEVICE_ATTR',a)
body=s[a:b]
shim=r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <stddef.h>
#include <sys/types.h>
struct tegra_dc {bool enabled;};
struct win {struct tegra_dc *dc;};
struct tegra_fb_info {struct win *win;bool legacy_enabled,legacy_dead,legacy_poisoned,dc_blanked,dc_trace_armed;int legacy_lock;};
struct fb_info {struct tegra_fb_info *par;};
struct device {struct fb_info *info;};struct device_attribute {int unused;};
static int info_locked,legacy_locked,missing;
static struct fb_info *dev_get_drvdata(struct device *d){return d->info;}
static int kstrtobool(const char *s,bool *b){if(!strcmp(s,"1")){*b=true;return 0;}if(!strcmp(s,"0")){*b=false;return 0;}return -EINVAL;}
static int lock_fb_info(struct fb_info *i){(void)i;assert(!info_locked);if(missing)return 0;info_locked=1;return 1;}
static void unlock_fb_info(struct fb_info *i){(void)i;assert(info_locked&&!legacy_locked);info_locked=0;}
static void mutex_lock(int *l){(void)l;assert(info_locked&&!legacy_locked);legacy_locked=1;}
static void mutex_unlock(int *l){(void)l;assert(info_locked&&legacy_locked);legacy_locked=0;}
#define WRITE_ONCE(x,y) ((x)=(y))
#define wingray_dc_checkpoint(...) ((void)0)
'''
main=r'''
int main(void){struct tegra_dc dc={true};struct win win={&dc};
 struct tegra_fb_info fb={.win=&win,.legacy_enabled=true};struct fb_info info={&fb};struct device dev={&info};
 assert(!fb.dc_trace_armed);
 assert(wingray_dc_test_store(&dev,0,"1",1)==1&&fb.dc_trace_armed);
 assert(wingray_dc_test_store(&dev,0,"0",1)==1&&!fb.dc_trace_armed);
 assert(wingray_dc_test_store(&dev,0,"bad",3)==-EINVAL&&!fb.dc_trace_armed);
 for(int i=0;i<5;i++){
  fb.legacy_enabled=true;fb.legacy_dead=fb.legacy_poisoned=fb.dc_blanked=false;dc.enabled=true;
  if(i==0)fb.legacy_enabled=false;if(i==1)fb.legacy_dead=true;if(i==2)fb.legacy_poisoned=true;if(i==3)fb.dc_blanked=true;if(i==4)dc.enabled=false;
  assert(wingray_dc_test_store(&dev,0,"1",1)==-EBUSY&&!fb.dc_trace_armed);
  fb.dc_trace_armed=true;assert(wingray_dc_test_store(&dev,0,"0",1)==-EBUSY&&fb.dc_trace_armed);fb.dc_trace_armed=false;
 }
 missing=1;assert(wingray_dc_test_store(&dev,0,"1",1)==-ENODEV);
 assert(!info_locked&&!legacy_locked);return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'gate.c').write_text(shim+body+main)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-fsanitize=undefined',str(p/'gate.c'),'-o',str(p/'gate')],check=True)
 subprocess.run([str(p/'gate')],check=True)
assert 'DEVICE_ATTR(wingray_dc_test, 0600' in s
assert 'if (!READ_ONCE(tegra_fb->dc_trace_armed))\n   return tegra_fb_wingray_blank' in s
h=(R/'sources/kernel-donor/drivers/staging/tegra/video/dc/wingray_trace.h').read_text()
for bad in ('tegra_dc_readl(', 'clk_get_rate(', 'readl(', 'writel(', 'spin_lock('): assert bad not in h
print('PASS actual gate: defaults off, lock order, arm/disarm, dead/poisoned/off/invalid guards; checkpoint helper has no MMIO/clock reads')
# Exercise the actual fixed shell request against temporary sysfs files.
with tempfile.TemporaryDirectory(prefix='xoom-dc-gate-') as d:
 p=Path(d);arm=p/'arm';blank=p/'blank';state=p/'state';state.write_text('0\n')
 bb=p/'busybox';bb.write_text('#!/bin/sh\ncase "$1" in\nid) echo 0; exit 0;;\nsleep) exit 0;;\ndmesg) echo "WG_DC85 fixture"; exit 0;;\nesac\nexec /usr/bin/busybox "$@"\n');bb.chmod(0o755)
 sh=(R/'diagnostic/fb-blank-test.sh').read_text().replace('/bin/busybox',str(bb))
 for a,b in [('/sys/class/graphics/fb0/wingray_dc_test',str(arm)),('/sys/class/graphics/fb0/blank',str(blank)),('/sys/class/graphics/fb0/state',str(state))]:sh=sh.replace(a,b)
 script=p/'test.sh';script.write_text(sh)
 arm.write_text('0\n');blank.write_text('0\n')
 out=subprocess.check_output(['/bin/sh',str(script)])
 assert arm.read_text()=='0\n' and b'DCTEST_ARMED_1' not in out
 out=subprocess.check_output(['/bin/sh',str(script),'--dc'])
 assert b'DCTEST_ARMED_1\n' in out and b'DCTEST_DISARM_RC 0\n' in out
 assert b'DCTEST_ARMED_AFTER 0\n' in out and blank.read_text()==arm.read_text()=='0\n'
 for preset in ('1\n',None):
  if preset is None:arm.unlink()
  else:arm.write_text(preset)
  blank.write_text('untouched\n')
  run=subprocess.run(['/bin/sh',str(script),'--dc'],capture_output=True)
  assert run.returncode!=0 and blank.read_text()=='untouched\n'
print('PASS actual shell: normal FBTEST leaves gate off; explicit DCTEST arms, restores, disarms; missing/already-armed gate rejected')
