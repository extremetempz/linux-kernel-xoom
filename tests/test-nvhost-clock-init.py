#!/usr/bin/env python3
"""Compile actual nvhost clock transaction with failing providers; no hardware."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_acm.c').read_text()
a=s.index('static void nvhost_module_release_clocks(');b=s.index('int nvhost_module_init(',a)
functions=s[a:b]
prefix=r'''
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
