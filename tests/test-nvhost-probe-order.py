#!/usr/bin/env python3
"""Actual host probe under stage failures; no register/IRQ/clock hardware."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1];p=root/'sources/kernel-donor/drivers/staging/tegra/video/host/host1x/host1x.c';source=p.read_text()
def fun(name):
 a=re.search(r'^static (?:int|void) '+name+r'\(',source,re.M).start();b=source.index('{',a);d=1;e=b+1
 while d:d+=(source[e]=='{')-(source[e]=='}');e+=1
 return source[a:e]
prefix=r'''
#define wingray_gputrace_engine(i,s,r) do {} while (0)
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define GFP_KERNEL 0
#define IORESOURCE_MEM 1
#define IORESOURCE_IRQ 2
#define EPROBE_DEFER 517
#define IS_ERR_OR_NULL(x) (!(x)||(intptr_t)(x)<0)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define dev_info(...) do{}while(0)
struct resource {unsigned long start,end;};static struct resource res[3]={{1,4},{5,5},{6,6}};
#define resource_size(r) ((r)->end-(r)->start+1)
struct nvhost_device_id{int x;};struct clk{int id;};static struct clk clks[3]={{0},{1},{2}};
struct nvhost_device {const char*name;int num_clks;struct clk*clk[3];struct{void*platform_data;}dev;};
struct nvhost_master{struct nvhost_device*dev;int info,syncpt,intr;void*reg_mem,*aperture,*memmgr;};
static struct nvhost_master *bound;
static int stage,fail,variant,regions,maps,intr_memory,manager,module,points,worker,irqs,users,published,debug,enabled[3];
static int step(void){return ++stage==fail;}
static void active(void){for(int i=0;i<3;i++)assert(enabled[i]==1);}
static struct resource *nvhost_get_resource(struct nvhost_device*d,int type,int n){if(variant==3)return NULL;return type==IORESOURCE_MEM?&res[0]:&res[1+n];}
static void *kzalloc(size_t n,int g){if(step())return NULL;return calloc(1,n);}
#define kfree free
static void *request_mem_region(unsigned long a,unsigned long b,const char*n){if(step())return NULL;regions=1;return &res[0];}
static void release_mem_region(unsigned long a,unsigned long b){assert(regions);regions=0;}
static void *ioremap(unsigned long a,unsigned long b){if(step())return NULL;maps=1;return &res[0];}
static void iounmap(void*a){assert(maps);maps=0;}
static int nvhost_alloc_resources(struct nvhost_master*h){intr_memory=1;return step()?-EIO:0;}
static void nvhost_free_resources(struct nvhost_master*h){intr_memory=0;}
static void *getmgr(void){if(step())return variant==1?NULL:(void*)(intptr_t)-EPROBE_DEFER;manager=1;return &manager;}
static void putmgr(void*m){assert(manager);manager=0;}
static struct{void*(*alloc_mgr)(void);void(*put_mgr)(void*);}ops={getmgr,putmgr};
#define mem_op() ops
static void nvhost_set_drvdata(struct nvhost_device*d,void*h){bound=h;}
static int nvhost_module_init(struct nvhost_device*d){if(step())return -EAGAIN;module=1;return 0;}
static void nvhost_module_abort_init(struct nvhost_device*d){assert(module&&!irqs);for(int i=0;i<3;i++)assert(!enabled[i]);module=0;}
static int clk_prepare_enable(struct clk*c){assert(module);if(step())return -EIO;assert(!enabled[c->id]);enabled[c->id]=1;return 0;}
static void clk_disable_unprepare(struct clk*c){assert(enabled[c->id]==1);enabled[c->id]=0;}
static unsigned long clk_get_rate(struct clk*c){return 166000000;}
static int nvhost_syncpt_init(struct nvhost_device*d,int*s){active();if(step())return -ENOMEM;points=1;return 0;}
static void nvhost_syncpt_deinit(int*s){assert(points);points=0;}
static int nvhost_intr_init(int*i,unsigned a,unsigned b){assert(points&&!published);if(step())return -ENOMEM;worker=1;return 0;}
static void nvhost_syncpt_reset(int*s){active();assert(points&&worker&&!users&&!published);}
static int nvhost_intr_start(int*i,unsigned long hz){active();assert(worker&&points&&!users&&!published);if(step())return -EBUSY;irqs=1;return 0;}
static void nvhost_intr_stop(int*i){active();assert(irqs);irqs=0;}
static void nvhost_intr_deinit(int*i){assert(worker);if(irqs){active();irqs=0;}worker=0;}
static int nvhost_user_init(struct nvhost_master*h){assert(!irqs&&points&&worker);for(int i=0;i<3;i++)assert(!enabled[i]);if(step())return -ENOMEM;users=1;return 0;}
static void nvhost_user_deinit(struct nvhost_master*h){assert(users);users=0;}
static int nvhost_bus_add_host(struct nvhost_master*h){assert(users&&module&&points&&worker);if(step())return -EIO;published=1;return 0;}
static void nvhost_debug_init(struct nvhost_master*h){assert(published);debug=1;}
'''
fixture=r'''
static void reset(void){stage=regions=maps=intr_memory=manager=module=points=worker=irqs=users=published=debug=0;bound=NULL;memset(enabled,0,sizeof(enabled));}
static void empty(void){assert(!regions&&!maps&&!intr_memory&&!manager&&!module&&!points&&!worker&&!irqs&&!users&&!published&&!debug&&!bound);for(int i=0;i<3;i++)assert(!enabled[i]);}
int main(void){int data=1;struct nvhost_device d={.name="host1x",.num_clks=3,.clk={clks,clks+1,clks+2},.dev={&data}};
 reset();fail=0;variant=0;assert(!nvhost_probe(&d,NULL));assert(stage==14&&published&&debug&&users&&worker&&points&&bound);free(bound);reset();
 for(fail=1;fail<=14;fail++){reset();assert(nvhost_probe(&d,NULL)<0);empty();}
 reset();fail=5;variant=1;assert(nvhost_probe(&d,NULL)==-EPROBE_DEFER);empty();
 reset();fail=0;variant=3;assert(nvhost_probe(&d,NULL)==-ENXIO);empty();
 reset();variant=0;d.dev.platform_data=NULL;assert(nvhost_probe(&d,NULL)==-ENXIO);empty();
 puts("PASS actual host probe: success, all 14 failure stages, deferred allocator and late publication; no hardware");}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'test.c';f.write_text(prefix+fun('nvhost_probe_enable_clocks')+'\n'+fun('nvhost_probe_disable_clocks')+'\n'+fun('nvhost_probe')+fixture)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined',str(f),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
