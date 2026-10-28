#!/usr/bin/env python3
"""Run actual CPCAP checked wake ownership and fault rollback with stubs."""
from pathlib import Path
import subprocess,tempfile
K=Path(__file__).resolve().parents[1]/'sources/kernel-donor'
s=(K/'drivers/mfd/motorola-cpcap.c').read_text()
def func(name):
 p=s.index(name+'(');start=s.rfind('\n',0,p)+1;b=s.index('{',p);end=b+1;depth=1
 while depth:
  depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]+'\n'
code=r'''
#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
#define CPCAP_REG_INTM2 1
#define CPCAP_REG_INTS2 2
#define CPCAP_REG_INT2 3
#define CPCAP_BIT_ON_I 128
#define CPCAP_BIT_ON_S 128
#define CPCAP_WINGRAY_ON_IRQ 23
struct irq_chip {const char *name;};
struct irq_data {struct irq_chip *chip; unsigned long hwirq; bool wake;};
struct device {void *data;};
struct device_attribute {int unused;};
struct spi_device {struct device dev;int irq;};
struct cpcap_ddata {struct spi_device *spi;int pwrkey_irq;bool pwrkey_irq_test;
 void *regmap;bool wake_arm_owned;int wake_arm_error,wake_arm_cleanup_error,wake_arm_lock;};
static struct irq_chip chip={"LIC"};
static struct irq_data parent,on;
static int reads,read_error_at,en,dis,en_error,dis_error;
static unsigned mask,sense,status;
static bool missing_parent,may_wake,post_pending,no_wake_flag,foreign_remains;
static struct irq_data *irq_get_irq_data(int irq) {return irq==59 ? (missing_parent?NULL:&parent) : &on;}
static bool irqd_is_wakeup_set(struct irq_data *d) {return d->wake;}
static bool device_may_wakeup(struct device *d) {(void)d;return may_wake;}
static int regmap_read(void *r,unsigned reg,unsigned *val) {
 (void)r;reads++; if(reads==read_error_at)return -EIO;
 *val=reg==1?mask:reg==2?sense:status;
 if(post_pending&&reads>3&&reg==3)*val|=128;
 return 0;
}
static int enable_irq_wake(int irq) {assert(irq==59);en++;if(en_error)return en_error;parent.wake=!no_wake_flag;return 0;}
static int disable_irq_wake(int irq) {assert(irq==59);dis++;if(dis_error)return dis_error;parent.wake=foreign_remains;return 0;}
static void mutex_lock(int *m){assert(!*m);*m=1;}
static void mutex_unlock(int *m){assert(*m);*m=0;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static int kstrtobool(const char *s,bool *v){if(!strcmp(s,"1")){*v=true;return 0;}if(!strcmp(s,"0")){*v=false;return 0;}return -EINVAL;}
static int dev_attr_wingray_wake_arm,removed,cleanup_logs;
static void device_remove_file(struct device *d,void *attr){(void)d;(void)attr;removed++;}
#define dev_err(...) (cleanup_logs++)
'''+func('cpcap_wingray_wake_idle')+func('cpcap_wingray_set_wake_arm')+func('wingray_wake_arm_store')+func('cpcap_wingray_wake_arm_remove')+r'''
static void reset(struct cpcap_ddata *c) {
 *c=(struct cpcap_ddata){.spi=c->spi,.pwrkey_irq=115,.pwrkey_irq_test=true};
 c->spi->dev.data=c;chip.name="LIC";parent=(struct irq_data){&chip,86,false};on=(struct irq_data){NULL,23,false};
 reads=read_error_at=en=dis=en_error=dis_error=0;mask=sense=status=0;
 missing_parent=post_pending=no_wake_flag=foreign_remains=false;may_wake=true;
}
int main(void){
 struct spi_device spi={.irq=59};struct cpcap_ddata c={.spi=&spi};
 reset(&c);
 assert(wingray_wake_arm_store(&spi.dev,NULL,"bad",3)==-EINVAL&&!en&&!dis&&!c.wake_arm_lock);
 assert(wingray_wake_arm_store(&spi.dev,NULL,"0",1)==1&&!dis);
 assert(wingray_wake_arm_store(&spi.dev,NULL,"1",1)==1&&c.wake_arm_owned&&parent.wake&&en==1&&!c.wake_arm_lock);
 assert(wingray_wake_arm_store(&spi.dev,NULL,"1",1)==1&&en==1);
 assert(wingray_wake_arm_store(&spi.dev,NULL,"0",1)==1&&!c.wake_arm_owned&&!parent.wake&&dis==1);
 assert(wingray_wake_arm_store(&spi.dev,NULL,"0",1)==1&&dis==1);
 for(int fault=0;fault<7;fault++){
  reset(&c);
  switch(fault){case 0:missing_parent=true;break;case 1:chip.name="GIC";break;case 2:parent.hwirq=85;break;
   case 3:on.hwirq=1;break;case 4:may_wake=false;break;case 5:c.pwrkey_irq_test=false;break;case 6:parent.wake=true;break;}
  assert(cpcap_wingray_set_wake_arm(&c,true)<0&&!en&&!dis&&!c.wake_arm_owned);
 }
 for(int fault=0;fault<3;fault++){
  reset(&c);if(fault==0)mask=128;else if(fault==1)sense=128;else status=128;
  assert(cpcap_wingray_set_wake_arm(&c,true)<0&&!en&&!dis);
 }
 for(int i=1;i<=6;i++){
  reset(&c);read_error_at=i;
  assert(cpcap_wingray_set_wake_arm(&c,true)==-EIO&&!c.wake_arm_owned);
  assert(en==(i>3)&&dis==(i>3));
 }
 reset(&c);en_error=-EPERM;assert(cpcap_wingray_set_wake_arm(&c,true)==-EPERM&&!c.wake_arm_owned&&!dis);
 reset(&c);no_wake_flag=true;assert(cpcap_wingray_set_wake_arm(&c,true)==-EIO&&en==1&&dis==1&&!c.wake_arm_owned);
 reset(&c);post_pending=true;assert(cpcap_wingray_set_wake_arm(&c,true)==-EBUSY&&dis==1&&!c.wake_arm_owned);
 reset(&c);post_pending=true;dis_error=-EIO;
 assert(cpcap_wingray_set_wake_arm(&c,true)==-EIO&&c.wake_arm_owned&&parent.wake);
 assert(c.wake_arm_error==-EBUSY&&c.wake_arm_cleanup_error==-EIO);
 dis_error=0;assert(cpcap_wingray_set_wake_arm(&c,false)==0&&!c.wake_arm_owned&&!parent.wake);
 reset(&c);assert(cpcap_wingray_set_wake_arm(&c,true)==0);dis_error=-EIO;
 assert(cpcap_wingray_set_wake_arm(&c,false)==-EIO&&c.wake_arm_owned);
 dis_error=0;foreign_remains=true;assert(cpcap_wingray_set_wake_arm(&c,false)==0&&!c.wake_arm_owned&&parent.wake);
 reset(&c);removed=cleanup_logs=0;cpcap_wingray_wake_arm_remove(&c);assert(removed==1&&!dis&&!cleanup_logs);
 reset(&c);assert(cpcap_wingray_set_wake_arm(&c,true)==0);cpcap_wingray_wake_arm_remove(&c);
 assert(!c.wake_arm_owned&&!parent.wake&&!c.wake_arm_lock&&dis==1);
 reset(&c);assert(cpcap_wingray_set_wake_arm(&c,true)==0);dis_error=-EIO;cpcap_wingray_wake_arm_remove(&c);
 assert(c.wake_arm_owned&&cleanup_logs==1&&!c.wake_arm_lock);
 return 0;
}
''' 
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert 'device_remove_file' in func('cpcap_wingray_wake_arm_remove')
assert '0600, wingray_wake_arm_show' in s
assert 'MOTOROLA_WINGRAY_PM_PREPARE' in (K/'drivers/mfd/Kconfig').read_text()
print('PASS actual parent wake-reference ownership, error propagation, rollback/retry and sysfs validation; physical wake untested')
