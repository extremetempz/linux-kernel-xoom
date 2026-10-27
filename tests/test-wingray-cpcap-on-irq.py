#!/usr/bin/env python3
"""Execute the actual ON IRQ handler and registration with faulted regmap IO.

This verifies software ownership, not physical key IRQs or wake from sleep.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / 'sources/kernel-donor'
source = (K / 'drivers/mfd/motorola-cpcap.c').read_text()

def function(name):
    pos = source.index(name + '(')
    start = source.rfind('\n', 0, pos) + 1
    brace = source.index('{', pos)
    end, depth = brace + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'

def execute(code):
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)
        (p / 'test.c').write_text(code)
        subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-fsanitize=undefined',
                        '-fno-sanitize-recover=all', str(p / 'test.c'),
                        '-o', str(p / 'test')], check=True)
        subprocess.run([str(p / 'test')], check=True)

execute(r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#define KEY_POWER 116
#define CPCAP_REG_INTS2 0x24
#define CPCAP_BIT_ON_S 0x80
#define IRQ_HANDLED 1
#define dev_info_ratelimited(...) ((void)0)
#define dev_err_ratelimited(...) ((void)0)
typedef int irqreturn_t;
struct device {int placeholder;};
struct spi_device {struct device dev;};
struct input_dev {int placeholder;};
struct cpcap_ddata {struct spi_device *spi;struct input_dev *pwrkey;
 void *regmap;unsigned pwrkey_irq_count,pwrkey_irq_errors;bool pwrkey_state;};
static int sense,error,events[4],n,syncs,wake_calls;
static int regmap_read(void *r,unsigned reg,unsigned *value){assert(reg==CPCAP_REG_INTS2);*value=sense;return error;}
static void pm_wakeup_event(struct device *d,unsigned ms){assert(ms==500);wake_calls++;}
static void input_report_key(struct input_dev *d,int key,int value){assert(key==116&&n<4);events[n++]=value;}
static void input_sync(struct input_dev *d){syncs++;}
''' + function('cpcap_wingray_on_thread') + r'''
int main(void){struct spi_device spi={0};struct input_dev input={0};
 struct cpcap_ddata c={.spi=&spi,.pwrkey=&input};
 for(int i=0;i<50;i++){
  n=syncs=0;sense=0x2bc;assert(cpcap_wingray_on_thread(123,&c)==IRQ_HANDLED);
  assert(n==1&&events[0]==1&&syncs==1&&c.pwrkey_state);
  n=syncs=0;assert(cpcap_wingray_on_thread(123,&c)==IRQ_HANDLED&&!n&&!syncs);
  sense=0x23c;assert(cpcap_wingray_on_thread(123,&c)==IRQ_HANDLED);
  assert(n==1&&events[0]==0&&syncs==1&&!c.pwrkey_state);
 }
 n=syncs=0;assert(cpcap_wingray_on_thread(123,&c)==IRQ_HANDLED);
 assert(n==2&&events[0]==1&&events[1]==0&&syncs==2);
 n=0;error=-EIO;sense=0x2bc;
 assert(cpcap_wingray_on_thread(123,&c)==IRQ_HANDLED&&!n&&!c.pwrkey_state);
 assert(c.pwrkey_irq_errors==1&&c.pwrkey_irq_count==152&&wake_calls==152);
 return 0;}
''')

execute(r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#define CPCAP_WINGRAY_ON_IRQ 23
#define CPCAP_REG_INTS2 0x24
#define CPCAP_REG_INTM2 0x14
#define CPCAP_REG_INT2 4
#define CPCAP_BIT_ON_S 0x80
#define CPCAP_BIT_ON_I 0x80
#define KEY_POWER 116
#define EV_KEY 1
#define IRQF_ONESHOT 0x2000
#define dev_info(...) ((void)0)
#define dev_err(...) ((void)0)
struct device {int placeholder;};
struct input_dev {const char *name,*phys;struct {struct device *parent;} dev;};
struct spi_device {struct device dev;int irq;};
struct irq_chip {const char *name;};
struct irq_data {struct irq_chip *chip;};
struct cpcap_ddata {struct spi_device *spi;void *irqdata[3],*regmap;
 struct input_dev *pwrkey;bool pwrkey_state;int pwrkey_irq;};
static struct irq_chip chip={"LIC"};static struct irq_data parent={&chip};
static struct input_dev input;
static int virq=222,fail_read,fail_mask,fail_write,fail_request,fail_register;
static int actions,wakeup,irq_requested,polls,report_value,mask=0xff7f;
static struct irq_data *irq_get_irq_data(int irq){assert(irq==59);return &parent;}
static int regmap_irq_get_virq(void *data,int n){assert(data==(void*)3&&n==23);return virq;}
static int regmap_read(void *r,unsigned reg,unsigned *v){assert(reg==CPCAP_REG_INTS2||reg==CPCAP_REG_INTM2);*v=reg==CPCAP_REG_INTS2?0x2bc:mask;return reg==CPCAP_REG_INTS2?fail_read:fail_mask;}
static int regmap_write(void *r,unsigned reg,unsigned v){assert(reg==4&&v==0x80);return fail_write;}
static struct input_dev *devm_input_allocate_device(struct device *d){return &input;}
static void input_set_capability(struct input_dev *d,int type,int key){assert(type==1&&key==116);}
static int input_register_device(struct input_dev *d){return fail_register;}
static void input_report_key(struct input_dev *d,int key,int v){assert(key==116);report_value=v;}
static void input_sync(struct input_dev *d){}
static int device_init_wakeup(void *d,bool enabled){wakeup=enabled;return 0;}
static int devm_add_action(struct device *d,void (*fn)(void *),void *p){actions++;return 0;}
static void cpcap_wingray_wakeup_disable(void *d){device_init_wakeup(d,false);}
static void cpcap_wingray_irq_status_remove(void *d){}
static int cpcap_wingray_on_thread(int irq,void *d){return 1;}
static int devm_request_threaded_irq(struct device *d,int irq,void *handler,int (*thread)(int,void*),int flags,const char *name,void *data){assert(irq==222&&!handler&&thread==cpcap_wingray_on_thread&&flags==IRQF_ONESHOT);irq_requested++;return fail_request;}
static int dev_attr_wingray_irq_status;
static int device_create_file(struct device *d,int *attr){return 0;}
static void device_remove_file(struct device *d,int *attr){}
''' + function('cpcap_register_irq_pwrkey') + r'''
int main(void){struct spi_device spi={.irq=59};struct cpcap_ddata c={.spi=&spi,.irqdata={0,0,(void*)3}};
 assert(!cpcap_register_irq_pwrkey(&c)&&c.pwrkey_irq==222&&c.pwrkey_state);
 assert(report_value==1&&wakeup&&irq_requested==1&&actions==2&&!polls);
 chip.name="GIC";assert(cpcap_register_irq_pwrkey(&c)==-EINVAL);chip.name="LIC";
 c.irqdata[2]=0;assert(cpcap_register_irq_pwrkey(&c)==-ENODEV);c.irqdata[2]=(void*)3;
 virq=0;assert(cpcap_register_irq_pwrkey(&c)==-EINVAL);virq=-EIO;assert(cpcap_register_irq_pwrkey(&c)==-EIO);virq=222;
 fail_read=-EIO;assert(cpcap_register_irq_pwrkey(&c)==-EIO);fail_read=0;
 fail_register=-ENOMEM;assert(cpcap_register_irq_pwrkey(&c)==-ENOMEM);fail_register=0;
 fail_write=-EIO;assert(cpcap_register_irq_pwrkey(&c)==-EIO);fail_write=0;
 fail_request=-EBUSY;assert(cpcap_register_irq_pwrkey(&c)==-EBUSY);fail_request=0;
 fail_mask=-EIO;assert(cpcap_register_irq_pwrkey(&c)==-EIO);fail_mask=0;
 mask=0xffff;assert(cpcap_register_irq_pwrkey(&c)==-EIO);
 return 0;}
''')

register = function('cpcap_register_irq_pwrkey')
assert 'schedule_delayed_work' not in register
assert 'regmap_update_bits' not in register
assert 'disable_irq' not in register
assert 'CPCAP_REG_INT2, CPCAP_BIT_ON_I' in register
assert 'regmap_irq_get_virq(cpcap->irqdata[2]' in register
for name in ('displaypm', 'displaydc', 'battery'):
    cfg = (K / f'arch/arm/configs/wingray_android44_{name}_defconfig').read_text()
    assert 'CONFIG_MFD_CPCAP_WINGRAY_IRQ_TEST=y' not in cfg
print('PASS actual ON IRQ handler/registration: domain23, LIC gate, key transitions, quick clicks, IO/errors, no polling/parent masking; hardware unverified')
