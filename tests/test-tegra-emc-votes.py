#!/usr/bin/env python3
"""Fault-test actual shared EMC clock callbacks; no clocks or voltage writes."""
from pathlib import Path
import resource, subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];TREE=ROOT/'sources/kernel-donor';PATH='drivers/staging/tegra/clk.c'
def fn(s,n):
 a=s.index(n+'(');b=s.rfind('\nstatic ',0,a)+1;e=s.index('{',a)+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[b:e]
PREFIX=r'''
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define SHARED_CLK_NB 4
#define container_of(ptr,type,member) ((type*)((char*)(ptr)-offsetof(type,member)))
struct clk {int unused;};struct clk_hw {struct clk *clk;};
static struct clk physical;static struct clk *emc_clk=&physical;
static struct shared_emc_clk {struct clk_hw hw;unsigned long rate;int enabled;} virtual_emc_clks[SHARED_CLK_NB];
static int calls,fail_at,fail_twice,errors;static unsigned long history[20],physical_rate;
static int clk_set_rate(struct clk *c,unsigned long rate) {
 assert(c==emc_clk&&calls<20);history[calls++]=rate;
 if(calls==fail_at||(fail_twice&&calls==fail_at+1))return -EIO;
 physical_rate=rate;return 0;
}
#define pr_debug(...) ((void)0)
#define pr_err(...) (++errors)
static void reset(void){memset(virtual_emc_clks,0,sizeof(virtual_emc_clks));calls=fail_at=fail_twice=errors=0;physical_rate=0;}
'''
MAIN=r'''
int main(int argc,char **argv){
 assert(argc==2);reset();struct shared_emc_clk *a=&virtual_emc_clks[0],*b=&virtual_emc_clks[1];
 a->rate=100;b->rate=300;
 if(!strcmp(argv[1],"rate")) {
  a->enabled=1;physical_rate=100;fail_at=1;
  assert(shared_emc_clk_set_rate(&a->hw,600,0)==-EIO);
  assert(a->rate==100&&physical_rate==100&&calls==2&&history[0]==600&&history[1]==100);
  fail_at=0;assert(shared_emc_clk_set_rate(&b->hw,900,0)==0&&calls==2);
 } else if(!strcmp(argv[1],"prepare")) {
  a->enabled=1;physical_rate=100;fail_at=1;
  assert(shared_emc_clk_prepare(&b->hw)==-EIO);
  assert(!b->enabled&&physical_rate==100&&calls==2);
  fail_at=0;assert(shared_emc_clk_prepare(&b->hw)==0&&b->enabled&&physical_rate==300);
  reset();physical_rate=600;assert(shared_emc_clk_prepare(&virtual_emc_clks[0].hw)==0);
  assert(!calls&&physical_rate==600);
 } else if(!strcmp(argv[1],"unprepare")) {
  a->enabled=b->enabled=1;physical_rate=300;
  shared_emc_clk_unprepare(&b->hw);assert(!b->enabled&&physical_rate==100&&calls==1);
  b->enabled=1;physical_rate=300;fail_at=2;shared_emc_clk_unprepare(&b->hw);
  assert(!b->enabled&&a->enabled&&errors==1&&physical_rate==300);
  shared_emc_clk_unprepare(&a->hw);assert(!a->enabled&&calls==2&&physical_rate==300);
 } else {
  assert(!strcmp(argv[1],"rollback"));a->enabled=1;physical_rate=100;fail_at=1;fail_twice=1;
  assert(shared_emc_clk_set_rate(&a->hw,600,0)==-EIO&&errors==1&&a->rate==100);
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-emc-votes-') as t:
 def run(s,n):
  p=Path(t)/n;p.with_suffix('.c').write_text(PREFIX+'\n'.join(fn(s,f) for f in ['update_emc_clk_rate','shared_emc_clk_prepare','shared_emc_clk_unprepare','shared_emc_clk_set_rate'])+MAIN)
  subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-but-set-variable','-fsanitize=undefined',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  return {case:subprocess.run([str(p),case],capture_output=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0))) for case in ['rate','prepare','unprepare','rollback']}
 for case,r in run((TREE/PATH).read_text(),'current').items():assert r.returncode==0,(case,r.stderr)
 old=subprocess.check_output(['git','-C',str(TREE),'show','77d1c0ed:'+PATH],text=True)
 for case,r in run(old,'before').items():assert r.returncode!=0 and b'Assertion' in r.stderr,(case,r.stderr)
print('PASS actual EMC vote error propagation, enable/disable aggregation and rollback reporting; old code fails four negative controls. DVFS remains disabled.')
