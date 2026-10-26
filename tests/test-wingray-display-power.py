#!/usr/bin/env python3
"""Run the actual Wingray fb backlight blank state with fault injection."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];K=ROOT/'sources/kernel-donor'
s=(K/'drivers/staging/tegra/video/fb.c').read_text()
def function(source,name):
 pos=source.index(name+'(');start=source.rfind('\n',0,pos)+1;brace=source.index('{',pos);end=brace+1;depth=1
 while depth:
  depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]+'\n'
code=r'''
#include <assert.h>
#include <errno.h>
#define FB_BLANK_UNBLANK 0
#define FB_BLANK_POWERDOWN 4
#define dev_info(...) ((void)0)
struct tegra_dc {int enabled;};
struct tegra_dc_win {struct tegra_dc *dc;unsigned flags;};
struct tegra_fb_info {struct tegra_dc_win *win;};
static int calls[8],count,bl_error;
static int tegra_wingray_backlight_power(struct tegra_dc *dc,int mode){(void)dc;calls[count++]=mode?2:7;return bl_error;}
'''+function(s,'tegra_fb_wingray_blank')+r'''
int main(void){struct tegra_dc dc={1};struct tegra_dc_win win={&dc,0};struct tegra_fb_info fb={&win};
 count=0;assert(!tegra_fb_wingray_blank(4,&fb)&&dc.enabled&&count==1&&calls[0]==2);
 count=0;assert(!tegra_fb_wingray_blank(0,&fb)&&dc.enabled&&count==1&&calls[0]==7);
 bl_error=-5;count=0;assert(tegra_fb_wingray_blank(4,&fb)==-5&&count==1);bl_error=0;
 for(int n=0;n<10;n++){assert(!tegra_fb_wingray_blank(0,&fb));assert(!tegra_fb_wingray_blank(4,&fb));assert(dc.enabled);}
 return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
# LP8550 actual status callback: power and framebuffer blank must zero effective
# brightness while preserving the requested brightness for unblank.
s=(K/'drivers/video/backlight/lp855x_bl.c').read_text()
code=r'''
#include <assert.h>
#include <stdbool.h>
#define IS_ENABLED(x) 1
#define dev_info(...) ((void)0)
#define FB_BLANK_UNBLANK 0
#define BL_CORE_SUSPENDED 1
#define BL_CORE_FBBLANK 2
#define PWM_BASED 1
#define REGISTER_BASED 2
typedef unsigned char u8;
struct lp855x {bool wingray_p3;int mode;struct {int reg_brightness;} *cfg;};
struct backlight_device {struct {int brightness,state,power,fb_blank,max_brightness;} props;struct lp855x *data;};
static int value,io_error;
static struct lp855x *bl_get_data(struct backlight_device *b){return b->data;}
static int lp855x_wingray_brightness(struct lp855x *p,int b){(void)p;value=b;return io_error;}
static void lp855x_pwm_ctrl(struct lp855x *p,int b,int max){(void)p;(void)max;value=b;}
static int lp855x_write_byte(struct lp855x *p,int reg,u8 b){(void)p;(void)reg;value=b;return 0;}
'''+function(s,'lp855x_bl_update_status')+r'''
int main(void){struct lp855x p={.wingray_p3=true};struct backlight_device b={.props={.brightness=128,.max_brightness=255},.data=&p};
 assert(!lp855x_bl_update_status(&b)&&value==128);
 b.props.power=4;assert(!lp855x_bl_update_status(&b)&&!value&&b.props.brightness==128);
 b.props.power=0;b.props.fb_blank=4;assert(!lp855x_bl_update_status(&b)&&!value);
 b.props.fb_blank=0;b.props.state=BL_CORE_FBBLANK;assert(!lp855x_bl_update_status(&b)&&!value);
 b.props.state=0;assert(!lp855x_bl_update_status(&b)&&value==128);
 b.props.brightness=0;assert(!lp855x_bl_update_status(&b)&&!value);
 io_error=-5;assert(lp855x_bl_update_status(&b)==-5);
 return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual fb/LP8550 callbacks: backlight-only blank/unblank, IO rollback, ten software cycles, retained brightness and power flags (no DC power-down; not hardware validation)')
