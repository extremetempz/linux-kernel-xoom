#!/usr/bin/env python3
"""Compile actual fixed-vote callbacks and registration against fault providers."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'sources/kernel-donor/drivers/staging/tegra/clk.c').read_text()
a=s.index('/* Diagnostic-only votes:');b=s.index('\n#endif',a)
body=s[a:b]
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define ARRAY_SIZE(a) ((int)(sizeof(a)/sizeof((a)[0])))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define pr_info(...) ((void)0)
struct clk{int id;};struct clk_hw{const struct clk_init_data *init;};struct clk_lookup{int id;};
struct clk_ops{int(*prepare)(struct clk_hw*);void(*unprepare)(struct clk_hw*);int(*is_enabled)(struct clk_hw*);unsigned long(*recalc_rate)(struct clk_hw*,unsigned long);long(*round_rate)(struct clk_hw*,unsigned long,unsigned long*);int(*set_rate)(struct clk_hw*,unsigned long,unsigned long);};
struct clk_init_data{const char *name;const struct clk_ops *ops;};
struct shared_emc_clk{struct clk_hw hw;unsigned long rate;int enabled;struct clk*registered;struct clk_lookup*lookup;};
enum{G3D,G2D,SHARED_CLK_NB};static struct shared_emc_clk virtual_emc_clks[SHARED_CLK_NB];static struct clk *emc_clk;
static struct clk physical,registered[2];static struct clk_lookup lookups[2];
static int compat=1,fault,step,refs,clks,aliases,put_count;static unsigned long physical_rate=600000000;
static int of_machine_is_compatible(const char*s){assert(!strcmp(s,"motorola,wingray"));return compat;}
static struct clk*clk_get_sys(void*d,const char*n){assert(!d&&!strcmp(n,"emc"));if(++step==fault)return(void*)(intptr_t)-EIO;refs++;return &physical;}
static unsigned long clk_get_rate(struct clk*c){assert(c==&physical);return physical_rate;}
static struct clk*clk_register(void*d,struct clk_hw*h){assert(!d&&h->init->ops);if(++step==fault)return(void*)(intptr_t)-ENOMEM;int i=clks++;assert(i<2);assert(!strcmp(h->init->name,i?"wingray_gr2d_emc":"wingray_gr3d_emc"));registered[i].id=i;return &registered[i];}
static struct clk_lookup*clkdev_create(struct clk*c,const char*n,const char*fmt,const char*client){assert(!strcmp(n,"emc")&&!strcmp(fmt,"%s"));assert(!strcmp(client,c->id?"gr2d":"gr3d"));if(++step==fault)return NULL;aliases++;lookups[c->id].id=c->id;return &lookups[c->id];}
static void clkdev_drop(struct clk_lookup*l){assert(l&&aliases>0);aliases--;}
static void clk_unregister(struct clk*c){assert(c&&clks>0);clks--;}
static void clk_put(struct clk*c){assert(c==&physical&&refs==1);refs--;put_count++;}
static int shared_emc_clk_is_enabled(struct clk_hw*h){return container_of(h,struct shared_emc_clk,hw)->enabled;}
static unsigned long shared_emc_clk_recalc_rate(struct clk_hw*h,unsigned long p){(void)p;return container_of(h,struct shared_emc_clk,hw)->rate;}
'''
main=r'''
static void reset(void){memset(virtual_emc_clks,0,sizeof(virtual_emc_clks));emc_clk=NULL;wingray_emc_rate=0;step=refs=clks=aliases=put_count=0;physical_rate=600000000;compat=1;}
int main(void){
 for(fault=1;fault<=5;fault++){reset();assert(register_wingray_emc()<0);assert(!refs&&!clks&&!aliases&&!emc_clk&&!wingray_emc_rate);}
 reset();fault=0;physical_rate=399999999;assert(register_wingray_emc()==-ERANGE);assert(!refs&&!clks&&!aliases&&put_count==1);
 reset();compat=0;assert(register_wingray_emc()==-ENODEV);assert(!step);
 reset();assert(!register_wingray_emc());assert(refs==1&&clks==2&&aliases==2);
 struct shared_emc_clk*v=&virtual_emc_clks[G3D];unsigned long parent=0;
 assert(!wingray_emc_set(&v->hw,400000000,0));assert(v->rate==400000000&&!v->enabled);
 assert(!wingray_emc_prepare(&v->hw)&&v->enabled);assert(physical_rate==600000000);
 assert(wingray_emc_round(&v->hw,600000001,&parent)==-ERANGE);
 assert(wingray_emc_set(&v->hw,600000001,0)==-ERANGE&&v->rate==400000000);
 physical_rate=500000000;assert(wingray_emc_set(&v->hw,100000000,0)==-EIO&&v->rate==400000000);
 wingray_emc_unprepare(&v->hw);assert(!v->enabled);assert(wingray_emc_prepare(&v->hw)==-EIO&&!v->enabled);
 emc_clk=NULL;assert(wingray_emc_round(&v->hw,1,&parent)==-ENODEV);
 puts("PASS fixed EMC actual callbacks/registration: bounds, physical-rate drift, exact engine aliases and all acquisition rollbacks; no DRAM setters linked (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+body+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
