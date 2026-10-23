#!/usr/bin/env python3
"""Compile actual driver functions with faulting clock providers; no hardware.

Only acquisition/prepare/unwind is covered. This does NOT validate voltage,
EMC ordering, PLL rollback or stock frequency safety and must not enable DVFS.
"""
from pathlib import Path
import resource
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT/'sources/kernel-donor'
PATH = 'drivers/cpufreq/tegra20-cpufreq.c'


def function(source, name):
    at = source.index(name + '(')
    start = source.rfind('\nstatic ', 0, at) + 1
    brace = source.index('{', at)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


PREFIX = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define __init
#define __exit
#define NUM_CPUS 2
#define CPUFREQ_TABLE_END (~1U)
#define CPUFREQ_ENTRY_INVALID (~0U)
static __attribute__((unused)) int of_machine_is_compatible(const char *s) {return !strcmp(s,"motorola,wingray");}
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct clk {int id;};
static struct clk clocks[5]={{0},{1},{2},{3},{4}};
static struct clk *cpu_clk=&clocks[1], *pll_x_clk=&clocks[2],
                  *pll_p_clk=&clocks[3], *emc_clk=&clocks[4];
static bool pll_x_prepared;
struct cpufreq_frequency_table {unsigned frequency;};
static struct cpufreq_frequency_table freq_table[]={{216000},{CPUFREQ_TABLE_END}};
struct cpufreq_policy {unsigned cpu,cur,max,suspend_freq; struct clk *clk;
                      struct {unsigned max;} user_policy;};
static int tegra_cpufreq_driver;
static int refs[5], enabled[5], get_fail, prepare_fail, parent_fail,
           generic_fail, register_fail, parent_calls, generic_calls, unregister_calls;
static void reset(void) {
 memset(refs,0,sizeof(refs));memset(enabled,0,sizeof(enabled));
 get_fail=prepare_fail=parent_fail=generic_fail=register_fail=0;
 parent_calls=generic_calls=unregister_calls=0;pll_x_prepared=false;
 cpu_clk=&clocks[1];pll_x_clk=&clocks[2];pll_p_clk=&clocks[3];emc_clk=&clocks[4];
}
static struct clk *clk_get_sys(const char *bus,const char *name) {
 int id;
 if(bus) {assert(!strcmp(bus,"cpu")&&!strcmp(name,"emc"));id=4;}
 else if(!strcmp(name,"cclk"))id=1;
 else if(!strcmp(name,"pll_x"))id=2;
 else {assert(!strcmp(name,"pll_p"));id=3;}
 if(get_fail==id)return (struct clk *)(intptr_t)(-100-id);
 ++refs[id];return &clocks[id];
}
static void clk_put(struct clk *c) {assert(!IS_ERR(c)&&refs[c->id]>0);--refs[c->id];}
static int clk_prepare_enable(struct clk *c) {
 assert(!IS_ERR(c));if(c->id==prepare_fail)return -EIO;
 ++enabled[c->id];return 0;
}
static void clk_disable_unprepare(struct clk *c) {assert(enabled[c->id]>0);--enabled[c->id];}
static int clk_set_parent(struct clk *c,struct clk *p) {
 assert(c==cpu_clk&&p==pll_p_clk);++parent_calls;return parent_fail?-EINVAL:0;
}
static int cpufreq_generic_init(struct cpufreq_policy *p,
 struct cpufreq_frequency_table *t,unsigned latency) {
 assert(p&&t==freq_table&&latency==300000);++generic_calls;
 return generic_fail?-EBUSY:0;
}
static int cpufreq_register_driver(int *d) {assert(d==&tegra_cpufreq_driver);return register_fail?-ENODEV:0;}
static void cpufreq_unregister_driver(int *d) {assert(d==&tegra_cpufreq_driver);++unregister_calls;}
'''
MAIN = r'''
static void zero_resources(void) {for(int i=1;i<=4;i++){assert(!refs[i]);assert(!enabled[i]);}}
int main(int argc,char **argv) {
 assert(argc==2);struct cpufreq_policy p={0};
 if(!strcmp(argv[1],"intermediate")) {
  reset();prepare_fail=2;
  assert(tegra_target_intermediate(&p,0)==-EIO);
  assert(parent_calls==0&&!pll_x_prepared);zero_resources();
  reset();parent_fail=1;assert(tegra_target_intermediate(&p,0)==-EINVAL);
  assert(parent_calls==1&&!pll_x_prepared);zero_resources();
  reset();assert(tegra_target_intermediate(&p,0)==0);
  assert(parent_calls==1&&pll_x_prepared&&enabled[2]==1);
 } else if(!strcmp(argv[1],"policy")) {
  reset();p.cpu=2;assert(tegra_cpu_init(&p)==-EINVAL);zero_resources();p.cpu=0;
  reset();prepare_fail=4;assert(tegra_cpu_init(&p)==-EIO);assert(!generic_calls);zero_resources();
  reset();prepare_fail=1;assert(tegra_cpu_init(&p)==-EIO);assert(!generic_calls);zero_resources();
  reset();generic_fail=1;assert(tegra_cpu_init(&p)==-EBUSY);zero_resources();
  reset();assert(tegra_cpu_init(&p)==0);assert(enabled[1]==1&&enabled[4]==1);
  assert(p.max==1000000&&p.user_policy.max==1000000&&p.suspend_freq==216000);
  assert(tegra_cpu_exit(&p)==0);zero_resources();
 } else {
  assert(!strcmp(argv[1],"driver"));
  for(int i=1;i<=4;i++){reset();get_fail=i;assert(tegra_cpufreq_init()==-100-i);zero_resources();}
  reset();register_fail=1;assert(tegra_cpufreq_init()==-ENODEV);zero_resources();
  reset();assert(tegra_cpufreq_init()==0);
  for(int i=1;i<=4;i++)assert(refs[i]==1);
  tegra_cpufreq_exit();assert(unregister_calls==1);zero_resources();
 }
 return 0;
}
'''


def compile_run(source, path):
    names = (['tegra_limit_wingray_frequencies'] if 'static void tegra_limit_wingray_frequencies(' in source else []) + ['tegra_target_intermediate','tegra_cpu_init','tegra_cpu_exit',
             'tegra_cpufreq_init','tegra_cpufreq_exit']
    c = path.with_suffix('.c')
    c.write_text(PREFIX+'\n'.join(function(source,n) for n in names)+MAIN)
    subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
                    '-Wno-unused-parameter',str(c),'-o',str(path)],check=True)
    return {case: subprocess.run([str(path),case],capture_output=True,
            preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            for case in ('intermediate','policy','driver')}


with tempfile.TemporaryDirectory(prefix='xoom-cpufreq-test-') as t:
    directory = Path(t)
    current = compile_run((TREE/PATH).read_text(),directory/'current')
    for case,result in current.items():
        assert result.returncode==0,(case,result.stderr.decode())
    old = subprocess.check_output(['git','-C',str(TREE),'show','3a12d776:'+PATH],text=True)
    negative = compile_run(old,directory/'before')
    for case,result in negative.items():
        assert result.returncode!=0 and b'Assertion' in result.stderr,(case,result.stderr)
print('PASS actual cpufreq acquisition/prepare/unwind fault paths; old source fails all three negative-control groups. DVFS remains disabled.')
