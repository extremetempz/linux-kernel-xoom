#!/usr/bin/env python3
"""Fault-test actual engine initialization and unpublished channel cleanup."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
def extract(file,name):
 s=(root/'sources/kernel-donor/drivers/staging/tegra/video/host'/file).read_text();a=s.index(name+'(');a=s.rfind('\n',0,a)+1;e=s.index('{',a)+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
prefix=r'''
#define wingray_gputrace_engine(i,s,r) do {} while (0)
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define EPROBE_DEFER 517
#define dev_info(...) ((void)0)
struct nvhost_device;struct nvhost_channel;
struct handler{void(*destroy)(struct handler*,struct nvhost_channel*);};
struct nvhost_channel{struct nvhost_device*dev;struct handler*ctxhandler;};
struct nvhost_device{int index;struct nvhost_channel*channel;};struct nvhost_master{void *memmgr,*nvhost_class;};
static struct nvhost_master host,*current;static struct nvhost_channel channel;
static int allocs,step,fail,context,module,published,freed,destroyed;
static int fault(void){return ++step==fail;}
static struct nvhost_master*nvhost_get_host(struct nvhost_device*d){(void)d;return current;}
static struct nvhost_channel*nvhost_alloc_channel(struct nvhost_device*d){(void)d;assert(current&&current->memmgr&&current->nvhost_class);if(fault())return NULL;allocs++;return &channel;}
static void destroy(struct handler*h,struct nvhost_channel*c){(void)h;assert(c==&channel&&context&&!module&&!published);context=0;destroyed++;}
static struct handler handler={destroy};
static int nvhost_channel_init(struct nvhost_channel*c,struct nvhost_master*h,int n){(void)h;(void)n;if(fault())return -ENOMEM;context=1;c->ctxhandler=&handler;c->dev->channel=c;return 0;}
static int nvhost_module_init(struct nvhost_device*d){(void)d;assert(context&&!published);if(fault())return -EIO;module=1;return 0;}
static int nvhost_client_user_init(struct nvhost_device*d){(void)d;assert(module&&context);if(fault())return -EBUSY;published=1;return 0;}
static void nvhost_module_abort_init(struct nvhost_device*d){(void)d;assert(module&&!published);module=0;}
static void nvhost_free_channel(struct nvhost_channel*c){assert(c==&channel&&!module&&!context&&!published&&!c->dev->channel);freed++;}
'''
main=r'''
static void reset(void){channel=(struct nvhost_channel){0};allocs=step=context=module=published=freed=destroyed=0;}
int main(void){struct nvhost_device dev={0};
 assert(nvhost_client_device_init(&dev)==-EPROBE_DEFER);assert(!allocs&&!step);
 current=&host;assert(nvhost_client_device_init(&dev)==-EPROBE_DEFER);assert(!allocs&&!step);
 host.memmgr=&host;assert(nvhost_client_device_init(&dev)==-EPROBE_DEFER);assert(!allocs&&!step);
 host.nvhost_class=&host;
 int errors[]={0,-ENODEV,-ENOMEM,-EIO,-EBUSY};
 for(fail=1;fail<=4;fail++){reset();assert(nvhost_client_device_init(&dev)==errors[fail]);assert(!module&&!context&&!published&&!dev.channel);assert(freed==(fail>1));assert(destroyed==(fail>2));}
 reset();fail=0;assert(!nvhost_client_device_init(&dev));assert(allocs==1&&step==4&&module&&context&&published&&dev.channel==&channel);
 puts("PASS actual engine init: host deferral, four failure stages, context cleanup and publication after module readiness (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+extract('nvhost_channel.c','nvhost_channel_abort_init')+extract('bus_client.c','nvhost_client_device_init')+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)

# Diagnostic reset is a fifth fallible stage before publication.
gpu_prefix = prefix + r'''
static int nvhost_module_prepare_client(struct nvhost_device*d){(void)d;assert(module&&context&&!published);return fault()?-ETIMEDOUT:0;}
'''
gpu_main=main.replace('0,-ENODEV,-ENOMEM,-EIO,-EBUSY','0,-ENODEV,-ENOMEM,-EIO,-ETIMEDOUT,-EBUSY').replace('fail<=4','fail<=5').replace('step==4','step==5').replace('four failure stages','five failure stages including unpublished reset')
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(gpu_prefix+extract('nvhost_channel.c','nvhost_channel_abort_init')+extract('bus_client.c','nvhost_client_device_init')+gpu_main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined','-DCONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST=1',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
