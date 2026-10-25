#!/usr/bin/env python3
"""Fault-test the actual legacy panel rail entry point; no device access."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1];s=(r/'sources/kernel-donor/drivers/staging/tegra/video/dc/dc.c').read_text();a=s.index('int tegra_dc_panel_enable_common(');b=s.index('\nvoid tegra_disable_backlight',a)
code='''#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#define TEGRA_DC_OUT_RGB 0
#define TEGRA_DC_OUT_HDMI 1
#define TEGRA_DC_OUT_DSI 2
#define IS_ERR_OR_NULL(x) (!(x))
#define WARN_ON(x) ((void)(x))
#define dev_err(...) ((void)0)
struct out {bool panel_enabled;int type;void *pnl_vdd,*lvds_vdd,*hdmi_vdd,*hdmi_pll;};
struct tegra_dc {struct out *out;};
static int compatible=1,err,calls;
static int of_machine_is_compatible(const char*s){assert(!strcmp(s,"motorola,wingray"));return compatible;}
static int regulator_enable(void*p){assert(p);calls++;return err;}
'''+s[a:b]+'''
int main(void){
 struct out out={.type=TEGRA_DC_OUT_RGB,.pnl_vdd=(void*)1};struct tegra_dc dc={&out};
 err=-EIO;assert(tegra_dc_panel_enable_common(&dc)==-EIO&&!out.panel_enabled&&calls==1);
 err=0;assert(tegra_dc_panel_enable_common(&dc)==1&&out.panel_enabled&&calls==2);
 assert(tegra_dc_panel_enable_common(&dc)==0&&calls==2);
 out.panel_enabled=false;out.pnl_vdd=NULL;assert(tegra_dc_panel_enable_common(&dc)==-ENODEV&&calls==2);
 compatible=0;assert(tegra_dc_panel_enable_common(&dc)==1&&out.panel_enabled&&calls==2);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(code)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual Wingray legacy panel rail: missing/failing supply vetoes activation; no duplicated enable; non-Wingray behavior preserved')
