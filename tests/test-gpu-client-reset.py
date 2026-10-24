#!/usr/bin/env python3
"""Fault-test actual unpublished engine reset interval; no hardware."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_acm.c').read_text();a=s.index('int nvhost_module_prepare_client(');e=s.index('{',a)+1;d=1
while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
prefix=r'''
#define wingray_gputrace_engine(i,s,r) do {} while (0)
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define to_nvhost_driver(d) (d)
struct nvhost_device;struct nvhost_driver{void(*prepare_clockoff)(void);void(*idle)(struct nvhost_device*);};
struct nvhost_device{struct {struct nvhost_driver*driver;}dev;int index,can_powergate,refcount,lock,idle_wq;void*rst;};
static int fault,stage,active,parent,asserted,deasserts,gates;
static int nvhost_module_busy_checked(struct nvhost_device*d){if(++stage==fault)return -EIO;active=parent=1;d->refcount++;return 0;}
static void mutex_lock_nested(int*l,int s){(void)s;assert(!*l);*l=1;}
static void mutex_unlock(int*l){assert(*l);*l=0;}
static int reset_control_assert(void*r){assert(r&&active&&parent);if(++stage==fault)return -ETIMEDOUT;asserted=1;return 0;}
static void usleep_range(int a,int b){assert(a==1000&&b==2000&&active&&parent&&asserted);}
static int reset_control_deassert(void*r){assert(r&&active&&parent&&asserted);deasserts++;return ++stage==fault?-EBUSY:0;}
static int to_state_clockgated_locked(struct nvhost_device*d){assert(d->lock&&!d->refcount&&active&&parent);active=parent=0;gates++;return 0;}
#define wake_up(w) ((void)(w))
'''
main=r'''
int main(void){struct nvhost_driver drv={0};struct nvhost_device dev={.dev={&drv},.index=1,.rst=&dev};
 int errors[]={0,-EIO,-ETIMEDOUT,-EBUSY};
 for(fault=1;fault<=3;fault++){stage=active=parent=asserted=deasserts=gates=0;assert(nvhost_module_prepare_client(&dev)==errors[fault]);assert(!active&&!parent&&!dev.refcount&&!dev.lock);assert(gates==(fault>1));}
 fault=stage=0;assert(!nvhost_module_prepare_client(&dev));assert(!active&&!parent&&!dev.refcount&&!dev.lock);
 dev.index=10;stage=0;assert(nvhost_module_prepare_client(&dev)==-EINVAL&&!stage);
 puts("PASS actual client reset: activation/assert/deassert faults, clocked reset, gated exit and balanced references (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+s[a:e]+main);subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
