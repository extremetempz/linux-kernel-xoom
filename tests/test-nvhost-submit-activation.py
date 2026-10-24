#!/usr/bin/env python3
"""Fault-test the actual host1x submit entry, with no MMIO or GPU commands."""
from pathlib import Path
import re
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'sources/kernel-donor/drivers/staging/tegra/video/host/host1x/host1x_channel.c').read_text()
a=re.search(r'^static int host1x_channel_submit\(',s,re.M).start(); e=s.index('{',a)+1; depth=1
while depth:
    depth+=(s[e]=='{')-(s[e]=='}');e+=1
function=s[a:e]
prelude=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32;
#define NV_HOST1X_CLASS_ID 1
#define NVHOST_OPCODE_NOOP 0
#define NVHOST_INTR_ACTION_SUBMIT_COMPLETE 1
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define dev_warn(...) ((void)0)
#define WARN(e,...) ((void)(e))
struct nvhost_syncpt { int unused; };
struct nvhost_device { int serialize, class; const char *name; };
struct nvhost_cdma {int unused;};
struct nvhost_channel {struct nvhost_device *dev; int submitlock; void *cur_ctx; struct nvhost_cdma cdma;};
struct nvhost_job {struct nvhost_channel *ch;struct {int has_timedout;} *hwctx;u32 syncpt_incrs,syncpt_end,syncpt_id;int num_waitchk,waitchk_mask,null_kickoff;void *memmgr,*waitchk;};
struct nvmap_client {int unused;};
static struct {struct nvhost_syncpt syncpt;int intr;} host;
static int fault, refs, touched, pushes, callbacks, held, freed, waiter;
#define nvhost_get_host(d) ((void)(d), &host)
static int nvhost_module_busy_checked(struct nvhost_device *d){(void)d;if(fault==1)return -EIO;refs++;return 0;}
static void nvhost_module_idle(struct nvhost_device *d){(void)d;assert(refs==1);refs--;}
static u32 nvhost_syncpt_read_max(struct nvhost_syncpt *s,u32 id){(void)s;(void)id;touched++;return 2;}
static int mutex_lock_interruptible(int *l){(void)l;if(fault==2)return -EINTR;held=1;return 0;}
static void mutex_unlock(int *l){(void)l;assert(held);held=0;}
static void *pre_submit_ctxsave(struct nvhost_job *j,void *ctx){(void)j;(void)ctx;return fault==3?(void *)(intptr_t)-ENOMEM:NULL;}
static void *nvhost_intr_alloc_waiter(void){if(fault==4)return NULL;return &waiter;}
static int nvhost_syncpt_wait_check(struct nvhost_syncpt *s,struct nvmap_client *m,int mask,void *w,int n){(void)s;(void)m;(void)mask;(void)w;(void)n;return fault==5?-EINVAL:0;}
static int nvhost_cdma_begin(struct nvhost_cdma *c,struct nvhost_job *j){(void)c;(void)j;return fault==6?-EBUSY:0;}
static int nvhost_opcode_setclass(int a,int b,int c){return a+b+c;}
static int host1x_uclass_wait_syncpt_r(void){return 0;}
static int nvhost_class_host_wait_syncpt(u32 a,u32 b){return a+b;}
static void nvhost_cdma_push(struct nvhost_cdma *c,int a,int b){(void)c;(void)a;(void)b;pushes++;}
static void submit_ctxsave(struct nvhost_job *j,void *w,void *ctx){(void)j;(void)w;(void)ctx;assert(refs&&held);}
static void submit_ctxrestore(struct nvhost_job *j){(void)j;}
static u32 nvhost_syncpt_incr_max(struct nvhost_syncpt *s,u32 id,u32 n){(void)s;(void)id;return n+2;}
static void submit_nullkickoff(struct nvhost_job *j,u32 n){(void)j;(void)n;pushes++;}
static void submit_gathers(struct nvhost_job *j){(void)j;pushes++;}
static void sync_waitbases(struct nvhost_channel *c,u32 end){(void)c;(void)end;}
static void nvhost_cdma_end(struct nvhost_cdma *c,struct nvhost_job *j){(void)c;(void)j;assert(refs&&held&&pushes);}
static void trace_nvhost_channel_submitted(const char *n,u32 a,u32 b){(void)n;(void)a;(void)b;}
static int nvhost_intr_add_action(int *intr,u32 id,u32 end,int kind,struct nvhost_channel *ch,void *w,void *ref){(void)intr;(void)id;(void)end;(void)kind;(void)ch;(void)ref;assert(w==&waiter);callbacks++;return 0;}
static void kfree(void *p){if(p){assert(p==&waiter);freed++;}}
'''
main=r'''
int main(void){
 struct nvhost_device d={0,1,"gr3d"};struct nvhost_channel ch={.dev=&d};
 struct nvhost_job job={.ch=&ch,.num_waitchk=1,.syncpt_incrs=1};
 int errors[]={0,-EIO,-EINTR,-ENOMEM,-ENOMEM,-EINVAL,-EBUSY};
 for(fault=1;fault<=6;fault++){
  refs=touched=pushes=callbacks=held=freed=0;
  assert(host1x_channel_submit(&job)==errors[fault]);
  assert(!refs&&!pushes&&!callbacks&&!held);
  if(fault==1)assert(!touched&&!freed);
 }
 fault=refs=pushes=callbacks=held=0;
 assert(!host1x_channel_submit(&job));assert(refs==1&&pushes&&callbacks==1&&!held);
 puts("PASS actual submit: activation failure prevents syncpoint/CDMA access; six early failure paths and success (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'test.c';p.write_text(prelude+function+main)
    subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
    subprocess.run([t+'/test'],check=True)
