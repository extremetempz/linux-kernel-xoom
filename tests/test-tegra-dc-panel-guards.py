#!/usr/bin/env python3
"""Exercise actual Decatf DC clock/backlight functions with provider stubs."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1];tree=root/'sources/kernel-donor';path='drivers/staging/tegra/video/dc/dc.c'
def function(text,name):
    at=text.index('void '+name+'(');start=text.index('{',at);depth=1;end=start+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[at:end]
prelude='''#include <stdbool.h>
#include <assert.h>
#define TEGRA_DC_OUT_RGB 0
#define IS_ERR_OR_NULL(x) (!(x))
#define WARN_ON(x) ((void)(x))
struct clk {bool enabled;};
struct tegra_dc_out {int type;void *bl_vdd;};
struct tegra_dc {struct clk *clk;struct tegra_dc_out *out;};
unsigned clk_calls,rate_calls,resume_calls,suspend_calls,reg_on,reg_off;unsigned long last_rate;
int tegra_is_clk_enabled(struct clk *c){return c->enabled;}
int clk_prepare_enable(struct clk *c){clk_calls++;c->enabled=true;return 0;}
int regulator_enable(void *r){assert(r);reg_on++;return 0;}
int regulator_disable(void *r){assert(r);reg_off++;return 0;}
'''
h=(tree/'drivers/staging/tegra/video/cmc623.h').read_text();enum=re.search(r'typedef enum \{\s*cmc623_type_lsi,.*?\} CMC623_type;',h,re.S).group();rates='\n'.join(re.findall(r'^#define CMC623F?_CLK_RATE.*$',h,re.M))
cmc='#ifdef CONFIG_FB_TEGRA_CMC623\n'+enum+'\n'+rates+'''
int cmc623_current_type;
void tegra_dvfs_set_rate(struct clk *c,unsigned long rate){assert(c);rate_calls++;last_rate=rate;}
void cmc623_resume(void){resume_calls++;}
void cmc623_suspend(void){suspend_calls++;}
#endif
'''
main='''int main(void){
 struct clk c={false};struct tegra_dc_out out={0,(void*)1};struct tegra_dc dc={&c,&out};
 tegra_dc_clk_enable(&dc);assert(clk_calls==1);
 tegra_dc_clk_enable(&dc);assert(clk_calls==1);
#ifdef CONFIG_FB_TEGRA_CMC623
 assert(rate_calls==1&&last_rate==CMC623_CLK_RATE);
 cmc623_current_type=cmc623_type_fujitsu;c.enabled=false;tegra_dc_clk_enable(&dc);assert(rate_calls==2&&last_rate==CMC623F_CLK_RATE);
#else
 assert(rate_calls==0);
#endif
 tegra_enable_backlight(&dc);tegra_disable_backlight(&dc);assert(reg_on==1&&reg_off==1);
#ifdef CONFIG_FB_TEGRA_CMC623
 assert(resume_calls==1&&suspend_calls==1);
#else
 assert(!resume_calls&&!suspend_calls);
#endif
 out.type=1;tegra_enable_backlight(&dc);tegra_disable_backlight(&dc);assert(reg_on==1&&reg_off==1);
 return 0;
}'''
with tempfile.TemporaryDirectory(prefix='xoom-panel-guards-') as temp:
 t=Path(temp)
 def build(source,name,enabled):
  body='\n'.join(function(source,n) for n in ['tegra_dc_clk_enable','tegra_enable_backlight','tegra_disable_backlight'])
  p=t/(name+'.c');p.write_text(prelude+cmc+body+main)
  return subprocess.run(['cc','-std=gnu11','-Wall','-Werror',*(['-DCONFIG_FB_TEGRA_CMC623'] if enabled else []),str(p),'-o',str(t/name)],capture_output=True)
 current=(tree/path).read_text()
 for enabled in [False,True]:
  name='cmc-on' if enabled else 'cmc-off';r=build(current,name,enabled);assert r.returncode==0,r.stderr.decode();subprocess.run([str(t/name)],check=True)
 old=subprocess.check_output(['git','-C',str(tree),'show','b6483deb:'+path],text=True)
 assert build(old,'old-no-cmc',False).returncode!=0,'Old unguarded source unexpectedly compiled'
print('PASS actual clock/backlight functions: CMC-off makes no Samsung/DVFS calls; CMC-on rates/hooks and generic regulator behavior retained. Old non-Samsung source fails as expected. No hardware executed.')
