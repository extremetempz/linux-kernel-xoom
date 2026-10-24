#!/usr/bin/env python3
"""Compile actual nvhost clock transaction with failing providers; no hardware."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_acm.c').read_text()
a=s.index('static void nvhost_module_release_clocks(');b=s.index('int nvhost_module_init(',a)
functions=s[a:b]
prefix=r'''
#define wingray_gputrace_engine(i,s,r) do {} while (0)
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define NVHOST_MODULE_MAX_CLOCKS 3
#define EPROBE_DEFER 517
#define IS_ERR(x) ((intptr_t)(x)<0)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define dev_err(d,...) do {(void)(d); logs++;} while(0)
struct clk {int id;unsigned long rate;};
struct nvhost_device {int dev,num_clks,emc_idx;bool is_emc_client;struct clk *clk[3];struct {const char *name;long default_rate;}clocks[3];};
static struct clk clocks[3];static int refs[3],enabled[3],logs,gets,sets,preps;
static int fail_get,fail_round,fail_prepare,fail_set,zero_round,zero_old,null_get,rollback_fail;
static struct clk *clk_get(void *dev,const char *name){int i=gets++;(void)dev;(void)name;if(i==fail_get)return(void*)(intptr_t)-EPROBE_DEFER;if(i==null_get)return NULL;refs[i]++;return &clocks[i];}
static long clk_round_rate(struct clk*c,long rate){return c->id==fail_round?-ERANGE:c->id==zero_round?0:rate;}
static unsigned long clk_get_rate(struct clk*c){return c->id==zero_old?0:c->rate;}
static int clk_prepare_enable(struct clk*c){int i=c->id;preps++;if(i==fail_prepare){fail_prepare=-1;return -EAGAIN;}enabled[i]++;return 0;}
static void clk_disable_unprepare(struct clk*c){assert(enabled[c->id]==1);enabled[c->id]--;}
static int clk_set_rate(struct clk*c,unsigned long rate){assert(enabled[c->id]);sets++;if(c->id==fail_set&&rate==200UL+c->id){c->rate=999;return -EIO;}if(rollback_fail&&rate==100UL+c->id)return -EBUSY;c->rate=rate;return 0;}
static void clk_put(struct clk*c){assert(c&&refs[c->id]==1&&!enabled[c->id]);refs[c->id]--;}
'''
fixture=r'''
static void reset(struct nvhost_device*d){memset(d,0,sizeof(*d));memset(refs,0,sizeof(refs));memset(enabled,0,sizeof(enabled));gets=sets=preps=logs=0;fail_get=fail_round=fail_prepare=fail_set=zero_round=zero_old=null_get=-1;rollback_fail=0;for(int i=0;i<3;i++){clocks[i]=(struct clk){i,100+i};d->clocks[i].name=i==2?"emc":"host1x";d->clocks[i].default_rate=200+i;}}
static void clean(struct nvhost_device*d){assert(!d->num_clks&&!d->is_emc_client&&!d->emc_idx);for(int i=0;i<3;i++)assert(!refs[i]&&!enabled[i]&&!d->clk[i]);}
int main(void){struct nvhost_device d;int cases=0;
 reset(&d);assert(!nvhost_module_init_clocks(&d));assert(d.num_clks==3&&d.is_emc_client&&d.emc_idx==2);for(int i=0;i<3;i++)assert(refs[i]==1&&!enabled[i]&&clocks[i].rate==200UL+i);nvhost_module_release_clocks(&d);clean(&d);cases++;
 for(int kind=0;kind<7;kind++)for(int at=0;at<3;at++){
  reset(&d);int expected=0;
  switch(kind){case 0:fail_get=at;expected=-EPROBE_DEFER;break;case 1:fail_round=at;expected=-ERANGE;break;case 2:fail_prepare=at;expected=-EAGAIN;break;case 3:fail_set=at;expected=-EIO;break;case 4:zero_round=at;expected=-EINVAL;break;case 5:zero_old=at;expected=-EINVAL;break;case 6:null_get=at;expected=-ENODEV;break;}
  assert(nvhost_module_init_clocks(&d)==expected);clean(&d);for(int i=0;i<3;i++)assert(clocks[i].rate==100UL+i);if(kind==0||kind==1||kind>=4)assert(!preps&&!sets);cases++;
 }
 reset(&d);fail_set=2;rollback_fail=1;assert(nvhost_module_init_clocks(&d)==-EIO);clean(&d);assert(logs==3);cases++;
 reset(&d);d.clocks[0].name=NULL;assert(!nvhost_module_init_clocks(&d));clean(&d);assert(!gets&&!preps&&!sets);cases++;
 printf("PASS %d actual nvhost clock acquisition/rate/rollback fixture cases; hardware untested\n",cases);}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+functions+fixture)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
# Initialization must stop before power/sysfs work after clock errors.
body=s[b:];assert body.index('if (err)\n\t\treturn err;')<body.index('mutex_init(&dev->lock)')
assert 'fail_clocks:\n\tnvhost_module_release_clocks(dev);' in body

# The host-only diagnostic must acquire exactly the named host clock without
# invoking any rate, voltage or enable provider during initialization.
diag_fixture = r'''
int main(void) {struct nvhost_device d;
 reset(&d);d.index=10;d.clocks[1].name=NULL;
 assert(!nvhost_module_init_clocks(&d));assert(d.num_clks==1&&refs[0]==1);
 assert(!sets&&!preps&&clocks[0].rate==100);nvhost_module_release_clocks(&d);clean(&d);
 reset(&d);d.index=10;d.clocks[1].name=NULL;fail_get=0;
 assert(nvhost_module_init_clocks(&d)==-EPROBE_DEFER);clean(&d);
 reset(&d);d.index=1;d.clocks[1].name=NULL;
 assert(nvhost_module_init_clocks(&d)==-EINVAL);clean(&d);
 reset(&d);d.index=10;d.clocks[0].name="gr3d";d.clocks[1].name=NULL;
 assert(nvhost_module_init_clocks(&d)==-EINVAL);clean(&d);
 reset(&d);d.index=10;d.clocks[1].name=NULL;zero_old=0;
 assert(nvhost_module_init_clocks(&d)==-EINVAL);clean(&d);
 puts("PASS actual host-only clock initialization: firmware rate retained, no provider writes/enables, missing/invalid inputs rejected");
}
'''
# Retain the reset/clean helper functions, replacing only this fixture's main.
helpers=fixture[:fixture.index('int main(void)')]
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix.replace('int dev,num_clks', 'int index,dev,num_clks')+functions+helpers+diag_fixture)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=undefined','-DCONFIG_TEGRA_GRHOST_WINGRAY_HOST_TEST=1',str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)

# GPU diagnostic must lower dividers before any enable, retain host rate,
# reject physical EMC fallback, and unwind setters without enabling clocks.
gpu_prefix=prefix.replace('int dev,num_clks','int index,dev,num_clks').replace('assert(enabled[c->id]);sets++','assert(!enabled[c->id]);sets++').replace('rate==200UL+c->id','rate==200000000UL')
gpu_prefix="static int last_stage,last_result;\n"+gpu_prefix.replace('#define wingray_gputrace_engine(i,s,r) do {} while (0)', '#define wingray_gputrace_engine(i,s,r) do {last_stage=(s);last_result=(r);} while (0)')
gpu_prefix += r'''
static int provider_bad;
static const char *__clk_get_name(struct clk*c){(void)c;return provider_bad?"emc":"wingray_gr3d_emc";}
'''
gpu_main=r'''
static void setup(struct nvhost_device*d){reset(d);d->index=1;d->clocks[0].name="gr3d";d->clocks[1].name="emc";d->clocks[2].name=NULL;clocks[0].rate=400000000;clocks[1].rate=400000000;provider_bad=0;}
int main(void){struct nvhost_device d;
 setup(&d);assert(!nvhost_module_init_clocks(&d));assert(!preps&&sets==2&&clocks[0].rate==200000000&&clocks[1].rate==400000000);nvhost_module_release_clocks(&d);clean(&d);
 setup(&d);provider_bad=1;assert(nvhost_module_init_clocks(&d)==-ENODEV);assert(!sets&&!preps);clean(&d);
 setup(&d);fail_set=0;assert(nvhost_module_init_clocks(&d)==-EIO);assert(!preps&&clocks[0].rate==400000000);clean(&d);
 setup(&d);fail_round=1;assert(nvhost_module_init_clocks(&d)==-ERANGE);assert(!sets&&!preps);clean(&d);
 setup(&d);zero_round=0;assert(nvhost_module_init_clocks(&d)==-EINVAL);assert(!sets&&!preps);clean(&d);
 setup(&d);d.index=2;d.clocks[0].name="epp";d.clocks[1].name=NULL;assert(!nvhost_module_init_clocks(&d));assert(clocks[0].rate==100000000&&!preps);nvhost_module_release_clocks(&d);clean(&d);
 setup(&d);d.index=10;d.clocks[0].name="host1x";d.clocks[1].name=NULL;assert(!nvhost_module_init_clocks(&d));assert(!sets&&!preps&&clocks[0].rate==400000000);nvhost_module_release_clocks(&d);clean(&d);
 setup(&d);zero_old=0;assert(nvhost_module_init_clocks(&d)==-EINVAL);assert(last_stage==0x105&&last_result==-EINVAL);clean(&d);
 setup(&d);fail_round=0;assert(nvhost_module_init_clocks(&d)==-ERANGE);assert(last_stage==0x104&&last_result==-ERANGE);clean(&d);
 setup(&d);fail_get=1;assert(nvhost_module_init_clocks(&d)==-EPROBE_DEFER);assert(last_stage==0x111&&last_result==-EPROBE_DEFER);clean(&d);
 puts("PASS actual GPU clock initialization: gated dividers, fixed host, EMC fallback rejection and rollback (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(gpu_prefix+functions+helpers+gpu_main)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-fsanitize=undefined','-DCONFIG_TEGRA_GRHOST_WINGRAY_GPU_TEST=1',str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
