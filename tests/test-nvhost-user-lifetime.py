#!/usr/bin/env python3
"""Exercise actual nvhost control-device registration cleanup; no real devices."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1];s=(root/'sources/kernel-donor/drivers/staging/tegra/video/host/host1x/host1x.c').read_text()
def fun(name):
 a=re.search(r'^static (?:int|void) '+name+r'\(',s,re.M).start();b=s.index('{',a);d=1;e=b+1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <sys/types.h>
#define THIS_MODULE ((void*)1)
#define IFACE_NAME "nvhost"
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct cdev{dev_t dev;void*owner;};struct nvhost_master{void*nvhost_class,*ctrl;struct cdev cdev;};
static int nvhost_ctrlops,cls,region,chars,node,stage,fail;
static int step(void){return ++stage==fail;}
static void*class_create(void*m,const char*n){(void)m;(void)n;if(step())return (void*)(intptr_t)-EIO;cls=1;return &cls;}
static int alloc_chrdev_region(dev_t*d,int b,int n,const char*s){(void)b;(void)n;(void)s;assert(cls);if(step())return -EBUSY;region=1;*d=5;return 0;}
static void cdev_init(struct cdev*c,void*ops){assert(ops==&nvhost_ctrlops);c->dev=0;}
static int cdev_add(struct cdev*c,dev_t d,int n){(void)n;assert(region);if(step())return -EINVAL;chars=1;c->dev=d;return 0;}
static void*device_create(void*c,void*p,dev_t d,void*x,const char*n){(void)p;(void)x;(void)n;assert(c==&cls&&chars&&d==5);if(step())return (void*)(intptr_t)-ENOMEM;node=1;return &node;}
static void device_destroy(void*c,dev_t d){assert(c==&cls&&node&&d==5);node=0;}
static void cdev_del(struct cdev*c){assert(chars&&c->dev==5&&!node);chars=0;}
static void unregister_chrdev_region(dev_t d,int n){(void)n;assert(region&&d==5&&!chars);region=0;}
static void class_destroy(void*c){assert(c==&cls&&cls&&!region&&!chars&&!node);cls=0;}
'''
fixture=r'''
int main(void){struct nvhost_master h={0};assert(!nvhost_user_init(&h));assert(cls&&region&&chars&&node);nvhost_user_deinit(&h);assert(!cls&&!region&&!chars&&!node&&!h.nvhost_class&&!h.ctrl);
 for(fail=1;fail<=4;fail++){stage=0;assert(nvhost_user_init(&h)<0);assert(!cls&&!region&&!chars&&!node&&!h.nvhost_class&&!h.ctrl);}
 puts("PASS actual nvhost userspace publication: success and four allocation/registration cleanup paths");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+fun('nvhost_user_deinit')+'\n'+fun('nvhost_user_init')+fixture)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
