#!/usr/bin/env python3
"""Execute the selected PM transaction and actual driver callback dispatch."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];K=ROOT/'sources/kernel-donor'
s=(K/'drivers/mfd/motorola-cpcap.c').read_text()
def func(source,name):
 p=source.index(name+'(');start=source.rfind('\n',0,p)+1;b=source.index('{',p);end=b+1;depth=1
 while depth:
  depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]+'\n'
generic=(K/'drivers/base/power/generic_ops.c').read_text()
code=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
struct device;
struct dev_pm_ops { int (*suspend)(struct device *);int (*resume)(struct device *);};
struct device_driver {const struct dev_pm_ops *pm;};
struct device {struct device_driver *driver;void *data,*of_node;int locked;};
struct cpcap_ddata {bool pm_test_active,pm_cycle_owned,wake_arm_owned;int wake_arm_lock;};
static bool prep=true,present=true,compatible=true,retain_on_arm_failure;
static int spi_bus_type,arm_error,disarm_error,arms,disarms,refs,dispatches;
static struct cpcap_ddata c;
static struct device target;
static bool wingray_pm_prepare_only(void){return prep;}
__attribute__((unused)) static bool wingray_pm_dpm_test_active(void){return false;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static bool mutex_trylock(int *m){if(*m)return false;*m=1;return true;}
static void mutex_unlock(int *m){assert(*m);*m=0;}
static bool device_trylock(struct device *d){return mutex_trylock(&d->locked);}
static void device_unlock(struct device *d){mutex_unlock(&d->locked);}
static bool of_device_is_compatible(void *node,const char *name){(void)node;(void)name;return compatible;}
static struct device *bus_find_device(void *bus,struct device *start,void *data,int (*match)(struct device *,void *)){
 (void)bus;(void)start; if(!present||!match(&target,data))return NULL;refs++;return &target;}
static void put_device(struct device *d){assert(d==&target&&refs==1);refs--;}
#define dev_info(...) ((void)0)
static int cpcap_wingray_set_wake_arm(struct cpcap_ddata *d,bool arm){
 assert(d->wake_arm_lock);dispatches++;
 if(arm){arms++;assert(!d->wake_arm_owned);if(!arm_error||retain_on_arm_failure)d->wake_arm_owned=true;return arm_error;}
 disarms++;assert(d->wake_arm_owned);if(!disarm_error)d->wake_arm_owned=false;return disarm_error;
}
'''+func(s,'cpcap_wingray_pm_suspend')+func(s,'cpcap_wingray_pm_resume')+r'''
static const struct dev_pm_ops cpcap_wingray_test_pm_ops={cpcap_wingray_pm_suspend,cpcap_wingray_pm_resume};
'''+func(s,'cpcap_wingray_pm_match')+func(generic,'pm_generic_suspend')+func(generic,'pm_generic_resume')+func(s,'wingray_cpcap_devicepm_test')+r'''
static struct device_driver driver={&cpcap_wingray_test_pm_ops};
static void reset(void){
 c=(struct cpcap_ddata){0};target=(struct device){.driver=&driver,.data=&c};
 prep=present=compatible=true;retain_on_arm_failure=false;
 arm_error=disarm_error=arms=disarms=refs=dispatches=0;
}
static void clean(void){assert(!refs&&!target.locked&&!c.wake_arm_lock&&!c.pm_test_active);}
int main(void){
 reset();assert(wingray_cpcap_devicepm_test()==0);assert(arms==1&&disarms==1&&!c.wake_arm_owned&&!c.pm_cycle_owned);clean();
 for(int n=0;n<20;n++){assert(wingray_cpcap_devicepm_test()==0);clean();}assert(arms==21&&disarms==21);
 reset();prep=false;assert(wingray_cpcap_devicepm_test()==-EOPNOTSUPP&&!dispatches);clean();
 reset();present=false;assert(wingray_cpcap_devicepm_test()==-ENODEV&&!dispatches);clean();
 reset();compatible=false;assert(wingray_cpcap_devicepm_test()==-ENODEV&&!dispatches);clean();
 reset();target.locked=1;assert(wingray_cpcap_devicepm_test()==-EBUSY&&!refs&&!dispatches);target.locked=0;clean();
 reset();c.wake_arm_lock=1;assert(wingray_cpcap_devicepm_test()==-EBUSY&&!dispatches);c.wake_arm_lock=0;clean();
 reset();c.wake_arm_owned=true;assert(wingray_cpcap_devicepm_test()==-EBUSY&&!dispatches&&c.wake_arm_owned);clean();
 reset();c.pm_cycle_owned=true;assert(wingray_cpcap_devicepm_test()==-EBUSY&&!dispatches);clean();
 reset();arm_error=-EIO;assert(wingray_cpcap_devicepm_test()==-EIO&&arms==1&&!disarms);clean();
 reset();arm_error=-EBUSY;retain_on_arm_failure=true;assert(wingray_cpcap_devicepm_test()==-EBUSY&&disarms==1&&!c.wake_arm_owned);clean();
 reset();disarm_error=-EIO;assert(wingray_cpcap_devicepm_test()==-EIO&&c.wake_arm_owned&&c.pm_cycle_owned);clean();
 int old=dispatches;assert(wingray_cpcap_devicepm_test()==-EBUSY&&dispatches==old);clean();
 reset();assert(cpcap_wingray_pm_suspend(&target)==-EOPNOTSUPP&&!dispatches);
 assert(cpcap_wingray_pm_resume(&target)==-EOPNOTSUPP&&!dispatches);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
# Extend the existing actual enter_state fixture, keeping the old assertions.
fixture=(ROOT/'tests/test-wingray-freezer.py').read_text()
fixture=fixture.replace('#define CONFIG_MOTOROLA_WINGRAY_DEVICEPM_TEST 0','#define CONFIG_MOTOROLA_WINGRAY_DEVICEPM_TEST device_cfg')
fixture=fixture.replace('static int wingray_cpcap_devicepm_test(void){assert(0);return -EIO;}',
 'static bool device_cfg=true;static int selected_calls,selected_error;\nstatic int wingray_cpcap_devicepm_test(void){selected_calls++;return selected_error;}')
fixture=fixture.replace(' (void)pm_states;', ''' (void)pm_states;
 reset();assert(enter_state(1,WINGRAY_PM_TEST_CPCAP)==0);
 assert(selected_calls==1&&prepares==1&&finishes==1&&!devices&&!holds&&!gfps&&!pm_mutex);
 reset();selected_error=-EIO;assert(enter_state(1,WINGRAY_PM_TEST_CPCAP)==-EIO&&finishes==1&&!devices);
 selected_error=0;selected_calls=0;device_cfg=false;reset();
 assert(enter_state(1,WINGRAY_PM_TEST_CPCAP)==-EOPNOTSUPP&&!selected_calls&&!prepares);
 device_cfg=true;reset();pm_mutex=1;assert(enter_state(1,WINGRAY_PM_TEST_CPCAP)==-EBUSY&&!selected_calls);
 reset();pm_test_level=4;assert(enter_state(1,WINGRAY_PM_TEST_CPCAP)==-EBUSY&&!selected_calls&&!prepares);
 reset();prepare_error=-EIO;assert(enter_state(1,WINGRAY_PM_TEST_CPCAP)==-EIO&&!selected_calls);
 reset();assert(enter_state(1,3)==-EOPNOTSUPP&&!selected_calls&&!prepares);
''')
exec(compile(fixture,str(ROOT/'tests/test-wingray-freezer.py'),'exec'),{'__file__':str(ROOT/'tests/test-wingray-freezer.py')})
main=(K/'kernel/power/main.c').read_text()
assert '0600, wingray_devicepm_test_show' in main
assert 'mutex_trylock' in func(main,'wingray_devicepm_test_show')
assert 'mutex_trylock' in func(main,'wingray_devicepm_test_store')
assert 'pm_generic_suspend(dev)' in func(s,'wingray_cpcap_devicepm_test')
assert 'pm_generic_resume(dev)' in func(s,'wingray_cpcap_devicepm_test')
print('PASS selected CPCAP actual callbacks/generic dispatch, ownership/unwind/faults and freezer dispatch; hardware untested')
