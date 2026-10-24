#!/usr/bin/env python3
"""Exercise actual IRQ start/stop and Tegra request-error propagation; no MMIO."""
from pathlib import Path
import subprocess,tempfile,re
root=Path(__file__).resolve().parents[1];tree=root/'sources/kernel-donor/drivers/staging/tegra/video/host'
def function(s,name):
 a=re.search(r'^(?:static )?(?:int|void) '+name+r'\(',s,re.M).start();b=s.index('{',a);d=1;e=b+1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
s=(tree/'nvhost_intr.c').read_text()
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#define u32 uint32_t
#define KERN_DEBUG ""
#define BUG_ON(x) assert(!(x))
#define printk(...) do{}while(0)
#define WLS_CANCELLED 1
#define WLS_HANDLED 2
struct list_head{int unused;};struct nvhost_waitlist{int state,refcount;struct list_head list;};
#define list_for_each_entry_safe(w,n,h,m) for((w)=NULL,(n)=NULL;((void)(n),(w)!=NULL);(w)=NULL)
#define list_empty(x) (1)
#define list_del(x) ((void)(x))
#define atomic_cmpxchg(a,b,c) (*(a))
#define kref_put(a,b) ((void)(a))
struct nvhost_intr_syncpt{struct list_head wait_head;};
struct nvhost_intr{int mutex;bool started;struct nvhost_intr_syncpt*syncpt;};
struct nvhost_master{int syncpt;};static struct nvhost_master master;
#define intr_to_dev(x) (&master)
static int nvhost_syncpt_nb_pts(int*x){(void)x;return 2;}
static int locked,stage1_fail,stage2_fail,irq1,irq2,requests1,requests2,writes,disables;
static void mutex_lock(int*x){(void)x;assert(!locked);locked=1;}
static void mutex_unlock(int*x){(void)x;assert(locked);locked=0;}
static int init(struct nvhost_intr*i){(void)i;assert(locked&&!irq1&&!irq2);requests1++;if(stage1_fail)return -EAGAIN;irq1=1;return 0;}
static int request(struct nvhost_intr*i){(void)i;assert(locked&&irq1&&!irq2);requests2++;if(stage2_fail)return -EBUSY;irq2=1;return 0;}
static void period(struct nvhost_intr*i,u32 p){(void)i;assert(locked&&irq1&&irq2&&p==166);writes++;}
static void free1(struct nvhost_intr*i){(void)i;assert(locked&&irq1);irq1=0;}
static void free2(struct nvhost_intr*i){(void)i;assert(locked&&irq2);irq2=0;}
static void disable(struct nvhost_intr*i){(void)i;assert(locked&&irq1&&irq2);disables++;}
static struct{int(*init_host_sync)(struct nvhost_intr*);int(*request_host_general_irq)(struct nvhost_intr*);void(*set_host_clocks_per_usec)(struct nvhost_intr*,u32);void(*free_syncpt_irq)(struct nvhost_intr*);void(*free_host_general_irq)(struct nvhost_intr*);void(*disable_all_syncpt_intrs)(struct nvhost_intr*);}ops={init,request,period,free1,free2,disable};
#define intr_op() ops
'''
fixture=r'''
int main(void){struct nvhost_intr_syncpt points[2];struct nvhost_intr i={.syncpt=points};
 nvhost_intr_stop(&i);assert(!disables&&!writes);
 stage1_fail=1;assert(nvhost_intr_start(&i,166000000)==-EAGAIN);assert(!i.started&&!irq1&&!irq2&&!locked&&!requests2&&!writes);
 stage1_fail=0;stage2_fail=1;assert(nvhost_intr_start(&i,166000000)==-EBUSY);assert(!i.started&&!irq1&&!irq2&&!locked&&!writes);
 stage2_fail=0;assert(!nvhost_intr_start(&i,166000000));assert(i.started&&irq1&&irq2&&writes==1);
 int first=requests1,second=requests2;assert(!nvhost_intr_start(&i,166000000));assert(first==requests1&&second==requests2&&writes==1);
 nvhost_intr_stop(&i);assert(!i.started&&!irq1&&!irq2&&!locked&&disables==1);
 nvhost_intr_stop(&i);assert(disables==1);
 assert(!nvhost_intr_start(&i,166000000));nvhost_intr_stop(&i);assert(disables==2&&!irq1&&!irq2);
 puts("PASS actual nvhost IRQ failure/unwind, duplicate-start, stop and restart paths");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+function(s,'nvhost_intr_start')+'\n'+function(s,'nvhost_intr_stop')+fixture)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
# The software initializer must not access registers or request IRQs.
initbody=function(s,'nvhost_intr_init')
assert 'intr_op().' not in initbody and 'intr->started = false;' in initbody
hw=(tree/'host1x/host1x_intr.c').read_text();body=function(hw,'t20_intr_init_host_sync')
assert body.startswith('static int ') and 'if (err)\n\t\treturn err;' in body
assert body.index('return err;')<body.index('writel(0, sync_regs + host1x_sync_ip_busy_timeout_r())')
assert 'flush_kthread_worker(&intr->worker);' in function(s,'nvhost_intr_deinit')
print('PASS source integration: software-only init, provider error return, worker drain')
