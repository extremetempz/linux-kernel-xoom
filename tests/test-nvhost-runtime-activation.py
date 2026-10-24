#!/usr/bin/env python3
"""Compile actual runtime activation/reference functions with faulted providers."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_acm.c').read_text()
def function(name):
    start = re.search(r'^(?:static )?(?:int|void) '+name+r'\(', source, re.M).start()
    pos = source.index('{', start); depth = 1; end = pos+1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}'); end += 1
    return source[start:end]
prelude = r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define NVHOST_POWER_STATE_RUNNING 1
#define NVHOST_POWER_STATE_CLOCKGATED 2
#define NVHOST_POWER_STATE_POWERGATED 3
#define dev_err(...) ((void)0)
#define to_nvhost_driver(d) (d)
#define to_nvhost_device(d) (d)
struct nvhost_device;
struct nvhost_driver { int (*finalize_clockon)(struct nvhost_device *); void (*finalize_poweron)(struct nvhost_device *); void (*busy)(struct nvhost_device *); };
struct clk { unsigned long rate; int refs; };
struct nvhost_device {
 struct { struct nvhost_driver *driver; struct nvhost_device *parent; } dev;
 int powerstate, index, num_clks, emc_idx, refcount, lock, powerstate_down;
 bool is_emc_client, poweron_pending;
 struct clk *clk[3]; struct { unsigned long default_rate; } clocks[3];
};
static struct nvhost_device host, engine;
static struct clk clocks[6];
static int enable_fail, round_fail, vote_fail, irq_fail, unpower_fail;
static int enabled, disabled, notifications, restores, irq_calls, rollback_fail;
static int rollback_logs, vote_calls, scheduled;
#undef dev_err
#define dev_err(...) ((void)++rollback_logs)
static void mutex_lock_nested(int *l, int subclass) { (void)subclass; assert(!*l); *l=1; }
static void mutex_unlock(int *l) { assert(*l); *l=0; }
static void cancel_delayed_work(int *w) { (void)w; }
static void schedule_powergating_locked(struct nvhost_device *d) { assert(d->lock); scheduled++; }
static int to_state_clockgated_locked(struct nvhost_device *d) {
 if (unpower_fail) return -EIO;
 d->powerstate=NVHOST_POWER_STATE_CLOCKGATED; return 0;
}
static long clk_round_rate(struct clk *c, unsigned long rate) { (void)c; return round_fail ? (round_fail==1 ? -ERANGE : 0) : (long)rate; }
static unsigned long clk_get_rate(struct clk *c) { return c->rate; }
static int clk_set_rate(struct clk *c, unsigned long rate) {
 vote_calls++; c->rate=rate;
 if (rate==400) return vote_fail ? -EIO : 0;
 if (rollback_fail) return -EBUSY;
 return 0;
}
static int clk_prepare_enable(struct clk *c) {
 int idx=(int)(c-clocks)+1;
 if (idx==enable_fail) return -ETIMEDOUT;
 c->refs++; enabled++; return 0;
}
static void clk_disable_unprepare(struct clk *c) { assert(c->refs==1); c->refs--; disabled++; }
static void nvhost_module_idle(struct nvhost_device *d) { assert(d->refcount>0); d->refcount--; }
static int clockon(struct nvhost_device *d) { irq_calls++; return ((irq_fail==1 && d==&host) || (irq_fail==2 && d==&engine)) ? -EIO : 0; }
static void poweron(struct nvhost_device *d) { (void)d; restores++; }
static void busy(struct nvhost_device *d) { assert(d->refcount>0 && !d->lock); notifications++; }
static struct nvhost_driver driver={clockon,poweron,busy};
static int nvhost_module_busy_checked(struct nvhost_device *dev);
'''
main = r'''
static void setup(void) {
 host=(struct nvhost_device){0}; engine=(struct nvhost_device){0};
 for(int i=0;i<6;i++) clocks[i]=(struct clk){100,0};
 host.dev.driver=engine.dev.driver=&driver; engine.dev.parent=&host;
 host.powerstate=engine.powerstate=NVHOST_POWER_STATE_CLOCKGATED;
 host.num_clks=1; host.clk[0]=&clocks[0]; host.index=10;
 engine.num_clks=3; engine.is_emc_client=true; engine.emc_idx=1;
 for(int i=0;i<3;i++){engine.clk[i]=&clocks[i+1];engine.clocks[i].default_rate=400;}
 enable_fail=round_fail=vote_fail=irq_fail=unpower_fail=0;
 enabled=disabled=notifications=restores=irq_calls=rollback_fail=rollback_logs=vote_calls=scheduled=0;
}
static void failed(int expected) {
 assert(nvhost_module_busy_checked(&engine)==expected);
 assert(!engine.refcount && !host.refcount);
 assert(engine.powerstate!=NVHOST_POWER_STATE_RUNNING);
 for(int i=1;i<4;i++) assert(!clocks[i].refs);
 assert(!engine.lock&&!host.lock);
 assert(clocks[2].rate==100);
 /* Retry after removing the provider fault must restore a usable module. */
 enable_fail=round_fail=vote_fail=irq_fail=unpower_fail=rollback_fail=0;
 assert(!nvhost_module_busy_checked(&engine));
 assert(engine.refcount==1&&host.refcount==1);
 assert(engine.powerstate==NVHOST_POWER_STATE_RUNNING);
 for(int i=1;i<4;i++)assert(clocks[i].refs==1);
 assert(clocks[2].rate==400);
}
int main(void) {
 setup(); assert(!nvhost_module_busy_checked(&engine));
 assert(engine.refcount==1&&host.refcount==1&&notifications==2&&irq_calls==2);
 int before=enabled; assert(!nvhost_module_busy_checked(&engine));
 assert(engine.refcount==2&&host.refcount==1&&enabled==before);
 setup(); enable_fail=1; failed(-ETIMEDOUT); /* parent */
 for(int i=2;i<=4;i++){setup();enable_fail=i;failed(-ETIMEDOUT);}
 setup();round_fail=1;failed(-ERANGE);
 setup();round_fail=2;failed(-EINVAL);
 setup();vote_fail=1;failed(-EIO);
 setup();irq_fail=1;failed(-EIO); /* parent IRQ blocks child */
 setup();irq_fail=2;failed(-EIO); /* engine IRQ after all enables */
 setup();engine.powerstate=NVHOST_POWER_STATE_POWERGATED;unpower_fail=1;failed(-EIO);
 setup();engine.powerstate=NVHOST_POWER_STATE_POWERGATED;enable_fail=4;
 assert(nvhost_module_busy_checked(&engine)==-ETIMEDOUT);
 assert(engine.poweron_pending&&!restores);
 enable_fail=0;assert(!nvhost_module_busy_checked(&engine));
 assert(!engine.poweron_pending&&restores==1);
 setup();vote_fail=rollback_fail=1;
 assert(nvhost_module_busy_checked(&engine)==-EIO);assert(rollback_logs==1);
 assert(!engine.refcount&&!host.refcount);
 puts("PASS actual runtime activation: parent/clock/EMC/IRQ failures, unwind, retries, pending restore and references (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'test.c'
    path.write_text(prelude+function('to_state_running_locked')+'\n'+function('nvhost_module_busy_checked')+main)
    subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(path),'-o',temp+'/test'],check=True)
    subprocess.run([temp+'/test'],check=True)
