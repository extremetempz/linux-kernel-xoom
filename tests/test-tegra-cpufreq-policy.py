#!/usr/bin/env python3
"""Check actual PLL-error result and Wingray table cap; no DVFS validation."""
from pathlib import Path
import re,resource,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];TREE=ROOT/'sources/kernel-donor';PATH='drivers/cpufreq/tegra20-cpufreq.c'
def fn(s,n):
 match=re.search(r'^static[^\n]*\b'+re.escape(n)+r'\(',s,re.M);b=match.start();a=match.end();e=s.index('{',a)+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[b:e]
PREFIX=r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#define CPUFREQ_TABLE_END (~1U)
#define CPUFREQ_ENTRY_INVALID (~0U)
struct cpufreq_frequency_table {unsigned frequency;};
struct cpufreq_policy {int unused;};struct clk {int id;};
static struct clk clocks[4];static struct clk *cpu_clk=&clocks[0],*pll_x_clk=&clocks[1],*pll_p_clk=&clocks[2],*emc_clk=&clocks[3];
static bool pll_x_prepared;static int wingray,pll_fail,parent_fail,drops;
static __attribute__((unused)) int of_machine_is_compatible(const char *s){assert(!strcmp(s,"motorola,wingray"));return wingray;}
static unsigned long clk_get_rate(struct clk *c){assert(c==pll_p_clk);return 216000000;}
static int clk_set_rate(struct clk *c,unsigned long r){assert(r>0);return c==pll_x_clk&&pll_fail?-EIO:0;}
static int clk_set_parent(struct clk *c,struct clk *p){assert(c==cpu_clk&&(p==pll_x_clk||p==pll_p_clk));return parent_fail?-EBUSY:0;}
static void clk_disable_unprepare(struct clk *c){assert(c==pll_x_clk);++drops;}
#define pr_err(...) ((void)0)
#define WARN_ON(x) ((void)(x))
'''
MAIN=r'''
int main(int argc,char **argv){
 assert(argc==2);struct cpufreq_policy p={0};
 if(!strcmp(argv[1],"errors")) {
  pll_fail=1;pll_x_prepared=true;
  assert(tegra_target(&p,3)==-EIO&&drops==1&&!pll_x_prepared);
  parent_fail=1;assert(tegra_target(&p,3)==-EIO); /* preserve first error */
  pll_fail=0;assert(tegra_target(&p,3)==-EBUSY);
  parent_fail=0;assert(tegra_target(&p,3)==0);
 } else {
  assert(!strcmp(argv[1],"cap"));
  wingray=0;tegra_limit_wingray_frequencies();int high=0;
  for(unsigned i=0;freq_table[i].frequency!=CPUFREQ_TABLE_END;i++)if(freq_table[i].frequency>1000000)++high;
  assert(high==3);wingray=1;tegra_limit_wingray_frequencies();
  int valid=0,invalid=0;
  for(unsigned i=0;freq_table[i].frequency!=CPUFREQ_TABLE_END;i++) {
   if(freq_table[i].frequency==CPUFREQ_ENTRY_INVALID){++invalid;continue;}
   assert(freq_table[i].frequency<=1000000);++valid;
  }
  assert(valid==8&&invalid==3);tegra_limit_wingray_frequencies();
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-cpufreq-policy-') as t:
 def run(s,n):
  table=re.search(r'static struct cpufreq_frequency_table freq_table\[\] = \{.*?\n\};',s,re.S).group()
  helper=fn(s,'tegra_limit_wingray_frequencies') if 'static void tegra_limit_wingray_frequencies(' in s else 'static void tegra_limit_wingray_frequencies(void) {}'
  p=Path(t)/n;p.with_suffix('.c').write_text(PREFIX+table+helper+fn(s,'tegra_target')+MAIN)
  subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  return {case:subprocess.run([str(p),case],capture_output=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0))) for case in ['errors','cap']}
 for case,r in run((TREE/PATH).read_text(),'current').items():assert r.returncode==0,(case,r.stderr)
 old=subprocess.check_output(['git','-C',str(TREE),'show','77d1c0ed:'+PATH],text=True)
 for case,r in run(old,'before').items():assert r.returncode!=0 and b'Assertion' in r.stderr,(case,r.stderr)
print('PASS PLL programming errors survive parent success; Wingray has no advertised overclock entries; other boards unchanged. Voltage/EMC transition correctness remains unvalidated.')
