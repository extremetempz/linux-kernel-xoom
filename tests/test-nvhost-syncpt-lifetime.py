#!/usr/bin/env python3
"""Run actual syncpoint sysfs init/unwind under allocation failures; no hardware."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1];s=(root/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_syncpt.c').read_text()
def fun(name):
 a=re.search(r'^(?:int|void) '+name+r'\(',s,re.M).start();b=s.index('{',a);d=1;e=b+1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define GFP_KERNEL 0
#define MAX_SYNCPT_LENGTH 5
#define S_IRUGO 0444
#define u32 uint32_t
typedef int atomic_t;
struct attribute{const char*name;int mode;};struct kobj_attribute{struct attribute attr;void(*show)(void);};
struct kobject{unsigned attrs;};struct nvhost_master;
struct nvhost_syncpt_attr{struct kobj_attribute attr;struct nvhost_master*host;int id;};
struct nvhost_syncpt{struct kobject*kobj;atomic_t*min_val,*max_val,*lock_counts;u32*base_val;struct nvhost_syncpt_attr*syncpt_attrs;struct kobject**syncpt_kobjs;};
struct nvhost_device{struct{struct kobject kobj;}dev;};static struct nvhost_master{int unused;}master;
#define syncpt_to_dev(x) (&master)
static const char *min_name="min",*max_name="max";
static void syncpt_min_show(void){}static void syncpt_max_show(void){}
#define sysfs_attr_init(x) ((void)(x))
static int stage,fail,live_kobjs,live_memory;
static int step(void){return ++stage==fail;}
static int nvhost_syncpt_nb_pts(struct nvhost_syncpt*s){(void)s;return 2;}
static int nvhost_syncpt_nb_bases(struct nvhost_syncpt*s){(void)s;return 1;}
static int nvhost_syncpt_nb_mlocks(struct nvhost_syncpt*s){(void)s;return 1;}
static void*kzalloc(size_t n,int f){(void)f;if(step())return NULL;live_memory++;return calloc(1,n);}
static void*kcalloc(size_t n,size_t m,int f){return kzalloc(n*m,f);}
static void kfree(void*p){if(p){assert(live_memory>0);live_memory--;free(p);}}
static struct kobject*kobject_create_and_add(const char*n,struct kobject*parent){(void)n;assert(parent);if(step())return NULL;live_kobjs++;return calloc(1,sizeof(struct kobject));}
static void kobject_put(struct kobject*k){if(k){assert(live_kobjs>0&&!k->attrs);live_kobjs--;free(k);}}
static unsigned bit(struct attribute*a){return !strcmp(a->name,"min")?1:2;}
static int sysfs_create_file(struct kobject*k,struct attribute*a){assert(k);if(step())return -EIO;assert(!(k->attrs&bit(a)));k->attrs|=bit(a);return 0;}
static void sysfs_remove_file(struct kobject*k,struct attribute*a){assert(k);k->attrs&=~bit(a);}
void nvhost_syncpt_deinit(struct nvhost_syncpt*);
'''
fixture=r'''
int main(void){struct nvhost_device d={0};struct nvhost_syncpt sp={0};fail=0;assert(!nvhost_syncpt_init(&d,&sp));int stages=stage;assert(live_kobjs==3&&live_memory==6);nvhost_syncpt_deinit(&sp);assert(!live_kobjs&&!live_memory);nvhost_syncpt_deinit(&sp);assert(!live_memory);
 for(fail=1;fail<=stages;fail++){memset(&sp,0,sizeof(sp));stage=0;assert(nvhost_syncpt_init(&d,&sp)<0);assert(!live_kobjs&&!live_memory&&!sp.kobj&&!sp.syncpt_kobjs);nvhost_syncpt_deinit(&sp);}
 printf("PASS actual syncpoint sysfs lifetime: success, %d failure stages, repeated cleanup; no hardware\n",stages);}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+fun('nvhost_syncpt_init')+'\n'+fun('nvhost_syncpt_deinit')+fixture)
 subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
