#!/usr/bin/env python3
"""Execute actual Wingray freezer-only dispatch and sysfs error handling."""
from pathlib import Path
import subprocess,tempfile
K=Path(__file__).resolve().parents[1]/'sources/kernel-donor'
s=(K/'kernel/power/suspend.c').read_text();main=(K/'kernel/power/main.c').read_text()
def func(source,name):
 p=source.index(name+'(');start=source.rfind('\n',0,p)+1;b=source.index('{',p);end=b+1;depth=1
 while depth:
  depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]+'\n'
code=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>
#include <errno.h>
#include <string.h>
typedef int suspend_state_t;
enum wingray_pm_test_mode { WINGRAY_PM_TEST_NONE, WINGRAY_PM_TEST_FREEZER, WINGRAY_PM_TEST_CPCAP, WINGRAY_PM_TEST_DPM, WINGRAY_PM_TEST_LATE, WINGRAY_PM_TEST_SYSCORE };
#define CONFIG_MOTOROLA_WINGRAY_DEVICEPM_TEST 0
#define CONFIG_MOTOROLA_WINGRAY_DPM_TEST 0
static int wingray_cpcap_devicepm_test(void){assert(0);return -EIO;}
#define CONFIG_PM_DEBUG 1
#define CONFIG_MOTOROLA_WINGRAY_FREEZER_TEST cfg
#define IS_ENABLED(x) (x)
#define PM_SUSPEND_FREEZE 1
#define TEST_NONE 0
#define TEST_CPUS 2
#define TEST_FREEZER 5
#define TEST_DEVICES 4
#define TEST_PLATFORM 3
static bool wingray_dpm_active;
#define TPS(x) (x)
#define trace_suspend_resume(...) ((void)0)
#define pr_warning(...) ((void)0)
#define pr_debug(...) ((void)0)
#define pr_info(...) ((void)0)
#define printk(...) ((void)0)
#define KERN_INFO ""
static bool cfg=true,prep=true;
static int pm_test_level,pm_mutex,wingray_freezer_lock,wingray_freezer_result;
static unsigned wingray_freezer_completed;
static const char *pm_states[]={"on","freeze"};
static int prepare_error,prepares,finishes,holds,devices,syncs,gfps,begins;
static bool wingray_pm_prepare_only(void){return prep;}
__attribute__((unused)) static bool wingray_pm_dpm_test_active(void){return false;}
static bool valid_state(int state){(void)state;return false;}
static bool mutex_trylock(int *m){if(*m)return false;*m=1;return true;}
static void mutex_unlock(int *m){assert(*m);*m=0;}
static void freeze_begin(void){begins++;}
static void sys_sync(void){syncs++;}
static void pm_suspend_clear_flags(void){}
static int suspend_prepare(int state){assert(state==1);prepares++;return prepare_error;}
static void suspend_finish(void){finishes++;}
static bool suspend_test(int level){return pm_test_level==level;}
static void msleep(unsigned ms){assert(ms==500&&pm_mutex);holds++;}
static void pm_restrict_gfp_mask(void){gfps++;}
static void pm_restore_gfp_mask(void){gfps--;}
static int suspend_devices_and_enter(int state){assert(state==1);devices++;return 0;}
struct kobject {int unused;};struct kobj_attribute {int unused;};
static bool sysfs_streq(const char *a,const char *b){return !strcmp(a,b);}
'''+func(s,'enter_state')+func(s,'wingray_pm_freezer_test')+func(main,'wingray_freezer_test_store')+r'''
static void reset(void){cfg=prep=true;pm_test_level=pm_mutex=wingray_freezer_lock=wingray_freezer_result=0;
 wingray_freezer_completed=0;prepare_error=prepares=finishes=holds=devices=syncs=gfps=begins=0;}
int main(void){
 (void)pm_states;
 reset();assert(wingray_freezer_test_store(NULL,NULL,"1",1)==1);
 assert(prepares==1&&finishes==1&&holds==1&&begins==1&&syncs==1&&!devices&&!gfps);
 assert(wingray_freezer_completed==1&&!pm_mutex&&!wingray_freezer_lock&&!pm_test_level);
 for(int error=-1;error>=-3;error--){reset();prepare_error=error;
  assert(wingray_pm_freezer_test()==error&&prepares==1&&!holds&&!finishes&&!devices&&!pm_mutex);}
 reset();cfg=false;assert(wingray_pm_freezer_test()==-EOPNOTSUPP&&!prepares);
 reset();prep=false;assert(wingray_pm_freezer_test()==-EOPNOTSUPP&&!prepares);
 reset();assert(enter_state(3,true)==-EOPNOTSUPP&&!prepares);
 reset();pm_mutex=1;assert(wingray_pm_freezer_test()==-EBUSY&&!prepares&&pm_mutex==1);
 reset();pm_test_level=4;assert(wingray_pm_freezer_test()==-EBUSY&&!prepares&&!pm_mutex);
 reset();assert(wingray_freezer_test_store(NULL,NULL,"0",1)==-EINVAL&&!prepares);
 reset();wingray_freezer_lock=1;assert(wingray_freezer_test_store(NULL,NULL,"1",1)==-EBUSY&&!prepares);
 reset();prepare_error=-EIO;assert(wingray_freezer_test_store(NULL,NULL,"1",1)==-EIO);
 assert(wingray_freezer_result==-EIO&&!wingray_freezer_completed&&!wingray_freezer_lock);
 reset();prep=false;assert(wingray_freezer_test_store(NULL,NULL,"1",1)==-ENODEV&&!prepares);
 reset();assert(enter_state(1,false)==-EOPNOTSUPP&&finishes==1&&!devices);
 reset();prep=false;assert(enter_state(1,false)==0&&devices==1&&finishes==1&&!gfps);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert '0600, wingray_freezer_test_show' in main
assert 'mutex_trylock' in func(main,'wingray_freezer_test_show')
assert 'mutex_lock(' not in func(main,'wingray_freezer_test_show')
assert 'return -EOPNOTSUPP;' in func(s,'pm_suspend')
assert 'return -EOPNOTSUPP;' in func(s,'suspend_devices_and_enter')

# The donor used to dereference suspend_ops when a freeze hook was absent.
# Execute the corrected source callbacks independently of the freezer test.
code=r'''
#include <assert.h>
typedef int suspend_state_t;
#define PM_SUSPEND_FREEZE 1
struct platform_freeze_ops {int (*begin)(void);void (*end)(void);};
struct platform_suspend_ops {int (*begin)(int);void (*end)(void);};
static struct platform_freeze_ops *freeze_ops;
static struct platform_suspend_ops *suspend_ops;
static int fb,fe,sb,se;
static int fbegin(void){fb++;return 7;}
static void fend(void){fe++;}
static int sbegin(int state){assert(state==3);sb++;return 9;}
static void send(void){se++;}
'''+func(s,'platform_suspend_begin')+func(s,'platform_resume_end')+r'''
int main(void){
 assert(platform_suspend_begin(1)==0);platform_resume_end(1);
 assert(platform_suspend_begin(3)==0);platform_resume_end(3);
 struct platform_freeze_ops f={fbegin,fend};struct platform_suspend_ops t={sbegin,send};
 freeze_ops=&f;suspend_ops=&t;
 assert(platform_suspend_begin(1)==7);platform_resume_end(1);assert(fb==1&&fe==1&&!sb&&!se);
 assert(platform_suspend_begin(3)==9);platform_resume_end(3);assert(sb==1&&se==1);
 freeze_ops=0;assert(platform_suspend_begin(1)==0);platform_resume_end(1);assert(sb==1&&se==1);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(code)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)

print('PASS actual freezer-only dispatch/hold/thaw, pre-entry errors, serialization and no device/CPU path; hardware untested')
