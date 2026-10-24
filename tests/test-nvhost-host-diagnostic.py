#!/usr/bin/env python3
"""Fault-test actual fixed diagnostic loop and suspend error propagation."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
def extract(source,name):
 a=re.search(r'^(?:static )?int (?:__init )?'+name+r'\(',source,re.M).start();e=source.index('{',a)+1;depth=1
 while depth:depth+=(source[e]=='{')-(source[e]=='}');e+=1
 return source[a:e]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define __init
#define pr_err(...) ((void)0)
#define pr_info(...) ((void)0)
struct nvhost_device{struct {void *parent;}dev;int num_clks,refcount;bool is_emc_client;void *clk[1];};
struct host{struct nvhost_device *dev;struct {bool started;}intr;};
static struct nvhost_device dev;static struct host host,*nvhost;
static int compatible,cycles,busies,suspends,fault;static unsigned long rate;
static int of_machine_is_compatible(const char*s){(void)s;return compatible;}
static unsigned long clk_get_rate(void*c){(void)c;return rate;}
static int nvhost_module_busy_checked(struct nvhost_device*d){busies++;if(busies==fault)return -EIO;d->refcount++;host.intr.started=true;return 0;}
static void nvhost_module_idle(struct nvhost_device*d){assert(d->refcount==1);d->refcount--;}
static int nvhost_module_suspend(struct nvhost_device*d){assert(!d->refcount);suspends++;host.intr.started=false;cycles++;return 0;}
'''
main=r'''
static void setup(void){dev=(struct nvhost_device){.num_clks=1};host=(struct host){.dev=&dev};nvhost=&host;compatible=1;cycles=busies=suspends=fault=0;rate=144000000;}
int main(void){
 setup();assert(!wingray_host_test_init());assert(cycles==3&&busies==3&&suspends==3&&!dev.refcount&&!host.intr.started);
 for(int i=1;i<=3;i++){setup();fault=i;assert(wingray_host_test_init()==-EIO);assert(cycles==i-1&&!dev.refcount&&!host.intr.started);}
 setup();nvhost=NULL;assert(wingray_host_test_init()==-ENODEV);assert(!busies);
 setup();compatible=0;assert(wingray_host_test_init()==-ENODEV);assert(!busies);
 setup();dev.is_emc_client=true;assert(wingray_host_test_init()==-EINVAL);assert(!busies);
 setup();dev.dev.parent=&dev;assert(wingray_host_test_init()==-EINVAL);assert(!busies);
 setup();dev.num_clks=2;assert(wingray_host_test_init()==-EINVAL);assert(!busies);
 setup();rate=0;assert(wingray_host_test_init()==-EINVAL);assert(!busies);
 puts("PASS actual host-only self-test loop: three cycles, activation faults and resource exclusions (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+extract((root/'sources/kernel-donor/drivers/staging/tegra/video/host/wingray_host_test.c').read_text(),'wingray_host_test_init')+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define ACM_SUSPEND_WAIT_FOR_IDLE_TIMEOUT 2
#define to_nvhost_driver(d) (d)
#define dev_info(...) ((void)0)
struct nvhost_device;
struct nvhost_driver{void(*suspend_ndev)(struct nvhost_device*);};
struct nvhost_device{struct {struct nvhost_driver*driver;}dev;int lock,index,powerstate_down;};
static int timeout,transition,callbacks;
#define wait_event_timeout(wq,cond,t) (timeout)
static void mutex_lock_nested(int*l,int s){(void)s;assert(!*l);*l=1;}
static void mutex_unlock(int*l){assert(*l);*l=0;}
static void cancel_delayed_work(int*w){(void)w;}
static int to_state_powergated_locked(struct nvhost_device*d){assert(d->lock);return transition;}
static void callback(struct nvhost_device*d){assert(!d->lock);callbacks++;}
'''
main=r'''
int main(void){struct nvhost_driver drv={callback};struct nvhost_device d={.dev={&drv}};
 timeout=0;assert(nvhost_module_suspend(&d)==-EBUSY);assert(!callbacks&&!d.lock);
 timeout=1;transition=-EIO;assert(nvhost_module_suspend(&d)==-EIO);assert(!callbacks&&!d.lock);
 transition=0;assert(!nvhost_module_suspend(&d));assert(callbacks==1&&!d.lock);
 puts("PASS actual suspend: transition failure returned before success callback (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+extract((root/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_acm.c').read_text(),'nvhost_module_suspend')+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
