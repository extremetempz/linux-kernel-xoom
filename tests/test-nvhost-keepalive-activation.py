#!/usr/bin/env python3
"""Fault-test actual channel acquisition with keepalive activation failure."""
from pathlib import Path
import re
import subprocess
import tempfile
source=(Path(__file__).resolve().parents[1]/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_channel.c').read_text()
a=re.search(r'^struct nvhost_channel \*nvhost_getchannel\(',source,re.M).start()
e=source.index('{',a)+1;depth=1
while depth:
    depth+=(source[e]=='{')-(source[e]=='}');e+=1
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define to_nvhost_driver(d) (d)
struct nvhost_device;
struct nvhost_driver{void (*init)(struct nvhost_device*);};
struct nvhost_device{struct {struct nvhost_driver *driver;} dev;bool exclusive,keepalive;};
struct nvhost_channel{struct nvhost_device *dev;int reflock,refcount,cdma;};
static int fail_init,fail_busy,busies,refs,inits,deinits;
static void mutex_lock(int*l){assert(!*l);*l=1;}
static void mutex_unlock(int*l){assert(*l);*l=0;}
static int nvhost_cdma_init(int*c){inits++;if(fail_init)return -ENOMEM;assert(!*c);*c=1;return 0;}
static void nvhost_cdma_deinit(int*c){assert(*c);*c=0;deinits++;}
static int nvhost_module_busy_checked(struct nvhost_device*d){(void)d;busies++;if(fail_busy)return -EIO;refs++;return 0;}
'''
main=r'''
int main(void){
 struct nvhost_driver drv={0};struct nvhost_device dev={.dev={&drv},.keepalive=true};
 struct nvhost_channel ch={.dev=&dev};
 fail_init=1;assert(!nvhost_getchannel(&ch));assert(!busies&&!ch.refcount&&!ch.cdma&&!ch.reflock);
 fail_init=0;fail_busy=1;assert(!nvhost_getchannel(&ch));assert(!refs&&!ch.refcount&&!ch.cdma&&deinits==1&&!ch.reflock);
 fail_busy=0;assert(nvhost_getchannel(&ch)==&ch);assert(refs==1&&ch.refcount==1&&ch.cdma);
 fail_busy=1;assert(!nvhost_getchannel(&ch));assert(refs==1&&ch.refcount==1&&ch.cdma&&deinits==1);
 fail_busy=0;assert(nvhost_getchannel(&ch)==&ch);assert(refs==2&&ch.refcount==2);
 dev.exclusive=true;int old=busies;assert(!nvhost_getchannel(&ch));assert(busies==old&&ch.refcount==2&&!ch.reflock);
 puts("PASS actual keepalive acquisition: failed activation unwinds new CDMA, preserves existing channel and reference counts (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'test.c';p.write_text(prefix+source[a:e]+main)
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
    subprocess.run([t+'/test'],check=True)
