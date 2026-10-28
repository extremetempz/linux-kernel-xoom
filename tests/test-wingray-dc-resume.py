#!/usr/bin/env python3
"""Execute the actual opt-in DC callbacks under fault injection/UBSan.

No physical display, frame completion or regulator behaviour is simulated
as evidence of hardware success.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
K = ROOT / 'sources/kernel-donor'

def function(source, name):
    pos = source.index(name + '(')
    start = source.rfind('\n', 0, pos) + 1
    brace = source.index('{', pos)
    end, depth = brace + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'

def execute(code):
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)
        (p / 'test.c').write_text(code)
        subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(p / 'test.c'), '-o', str(p / 'test')], check=True)
        subprocess.run([str(p / 'test')], check=True)

mode = (K / 'drivers/staging/tegra/video/dc/mode.c').read_text()
execute(r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#define IS_ENABLED(x) option
#define TEGRA_DC_OUT_RGB 0
#define TEGRA_DC_OUT_HDMI 1
#define TEGRA_DC_MODE_FLAG_NEG_H_SYNC 1
#define TEGRA_DC_MODE_FLAG_NEG_V_SYNC 2
#define FB_SYNC_HOR_HIGH_ACT 1
#define FB_SYNC_VERT_HIGH_ACT 2
#define CONFIG_TEGRA_HDMI_74MHZ_LIMIT 1
#define KHZ2PICOS(x) (1000000000UL / (x))
#define PICOS2KHZ(x) (1000000000UL / (x))
#define dev_info(...) ((void)0)
#define dev_err(...) ((void)0)
struct tegra_dc_mode {int pclk,rated_pclk,h_ref_to_sync,v_ref_to_sync,h_sync_width,
 v_sync_width,h_back_porch,v_back_porch,h_active,v_active,h_front_porch,
 v_front_porch,stereo_mode,flags;};
struct fb_videomode {unsigned pixclock,hsync_len,vsync_len,left_margin,
 upper_margin,xres,yres,right_margin,lower_margin,sync;};
struct output {int type,n_modes;struct tegra_dc_mode *modes;};
struct tegra_dc {struct output *out;struct tegra_dc_mode mode;};
static int option=1;
static bool of_machine_is_compatible(const char *s){return !strcmp(s,"motorola,wingray");}
static void calc_ref_to_sync(struct tegra_dc_mode *m){m->h_ref_to_sync=0;m->v_ref_to_sync=1;}
static bool check_ref_to_sync(struct tegra_dc_mode *m){(void)m;return true;}
static int tegra_dc_set_mode(struct tegra_dc *dc,const struct tegra_dc_mode *m){dc->mode=*m;return 0;}
''' + function(mode, 'tegra_dc_set_fb_mode') + r'''
int main(void){
 struct tegra_dc_mode native={.pclk=66400000,.h_ref_to_sync=11,.v_ref_to_sync=1,
 .h_sync_width=26,.v_sync_width=6,.h_back_porch=12,.v_back_porch=3,
 .h_active=1280,.v_active=800,.h_front_porch=45,.v_front_porch=3};
 struct output out={.type=0,.n_modes=1,.modes=&native};
 struct tegra_dc dc={.out=&out};
 struct fb_videomode m={.pixclock=KHZ2PICOS(66400),.hsync_len=26,
 .vsync_len=6,.left_margin=12,.upper_margin=3,.xres=1280,.yres=800,
 .right_margin=45,.lower_margin=3};
 option=0;assert(!tegra_dc_set_fb_mode(&dc,&m,false));
 assert(dc.mode.h_ref_to_sync==0 && dc.mode.pclk==66401000);
 option=1;
 for(int i=0;i<20;i++){
  assert(!tegra_dc_set_fb_mode(&dc,&m,false));
  assert(!memcmp(&dc.mode,&native,sizeof(native)));
 }
 assert(tegra_dc_set_fb_mode(&dc,&m,true)==-EINVAL);
 m.xres--;assert(tegra_dc_set_fb_mode(&dc,&m,false)==-EINVAL);m.xres++;
 m.pixclock++;assert(tegra_dc_set_fb_mode(&dc,&m,false)==-EINVAL);m.pixclock--;
 m.left_margin++;assert(tegra_dc_set_fb_mode(&dc,&m,false)==-EINVAL);m.left_margin--;
 out.modes=0;assert(tegra_dc_set_fb_mode(&dc,&m,false)==-EINVAL);
 return 0;
}
''')

fb = (K / 'drivers/staging/tegra/video/fb.c').read_text()
execute(r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#define DC_N_WINDOWS 3
#define wingray_dc_checkpoint(dc,phase,value) ((void)0)
#define TEGRA_WIN_FLAG_ENABLED 1
#define FB_BLANK_UNBLANK 0
#define FB_BLANK_POWERDOWN 4
#define DC_DISP_REF_TO_SYNC 0
#define DC_CMD_DISPLAY_COMMAND 1
#define DC_DISP_DISP_CLOCK_CONTROL 2
#define BIT(n) (1U << (n))
#define dev_info(...) ((void)0)
#define dev_err(...) ((void)0)
struct tegra_dc_win {unsigned flags;unsigned long address;unsigned stride;};
struct tegra_dc {int enabled,disable_work;struct {int h_ref_to_sync,v_ref_to_sync;} mode;};
struct tegra_fb_info {struct tegra_dc_win *win;struct tegra_dc *mock_dc;
 int legacy_lock;bool legacy_enabled,legacy_dead,legacy_poisoned,dc_blanked;
 unsigned dc_saved_flags[3];};
/* Match the actual win->dc member while keeping mock scanout attributes. */
'''.replace('unsigned flags;unsigned long', 'struct tegra_dc *dc;unsigned flags;unsigned long') + r'''
static struct tegra_dc_win windows[3];
static int locked,off_error,on_error,enable_error,update_error,sync_result=5;
static int power=0,disable_count,update_count,missing,bad_ref;
static unsigned long tegra_dc_readl(struct tegra_dc *d,int r){assert(d->enabled&&power==4);return r?0:bad_ref?0:0x1000b;}
static void mutex_lock(int *p){(void)p;assert(!locked);locked=1;}
static void mutex_unlock(int *p){(void)p;assert(locked);locked=0;}
static void cancel_delayed_work_sync(int *p){(void)p;assert(!locked);}
static struct tegra_dc_win *tegra_dc_get_window(struct tegra_dc *d,int i){(void)d;assert(locked);return missing?0:&windows[i];}
static int tegra_wingray_backlight_power(struct tegra_dc *d,int p){(void)d;assert(locked);if(p?off_error:on_error)return p?off_error:on_error;power=p;return 0;}
static void tegra_dc_disable(struct tegra_dc *d){assert(locked);assert(power==4);d->enabled=0;disable_count++;for(int i=0;i<3;i++)windows[i].flags&=~1U;}
static void tegra_dc_enable(struct tegra_dc *d){assert(locked);assert(power==4);d->enabled=!enable_error;}
static int tegra_dc_update_windows(struct tegra_dc_win **w,int n){assert(locked);assert(n==3);assert(power==4);for(int i=0;i<n;i++)assert(w[i]==&windows[i]);update_count++;return update_error;}
static int tegra_dc_sync_windows(struct tegra_dc_win **w,int n){(void)w;assert(locked&&n==3&&power==4);return sync_result;}
''' + function(fb, 'tegra_fb_wingray_dc_blank') + r'''
int main(void){
 struct tegra_dc dc={.enabled=1,.mode={11,1}};
 struct tegra_fb_info fb={.win=&windows[0],.mock_dc=&dc,.legacy_enabled=true};
 for(int i=0;i<3;i++){windows[i].dc=&dc;windows[i].address=0x1000+i*0x2000;windows[i].stride=5120;}
 /* fb window 0 deliberately inactive; HWC uses windows 1 and 2. */
 windows[0].flags=0;windows[1].flags=3;windows[2].flags=9;
 for(int i=0;i<20;i++){
  assert(!tegra_fb_wingray_dc_blank(4,&fb));assert(fb.dc_blanked&&!dc.enabled&&power==4);
  assert(fb.dc_saved_flags[0]==0&&fb.dc_saved_flags[1]==3&&fb.dc_saved_flags[2]==9);
  int before=disable_count;assert(!tegra_fb_wingray_dc_blank(4,&fb)&&disable_count==before);
  assert(!tegra_fb_wingray_dc_blank(0,&fb));assert(!fb.dc_blanked&&dc.enabled&&power==0);
  assert(windows[0].flags==0&&windows[1].flags==3&&windows[2].flags==9);
  for(int j=0;j<3;j++)assert(windows[j].address==(unsigned long)(0x1000+j*0x2000)&&windows[j].stride==5120);
 }
 off_error=-EIO;assert(tegra_fb_wingray_dc_blank(4,&fb)==-EIO&&!fb.dc_blanked&&dc.enabled);off_error=0;
 assert(!tegra_fb_wingray_dc_blank(4,&fb));
 enable_error=1;assert(tegra_fb_wingray_dc_blank(0,&fb)==-EIO&&fb.dc_blanked&&power==4);enable_error=0;
 update_error=-EIO;assert(tegra_fb_wingray_dc_blank(0,&fb)==-EIO&&fb.dc_blanked&&power==4);update_error=0;
 sync_result=0;assert(tegra_fb_wingray_dc_blank(0,&fb)==-ETIMEDOUT&&fb.dc_blanked&&power==4);
 sync_result=-EINTR;assert(tegra_fb_wingray_dc_blank(0,&fb)==-EINTR&&fb.dc_blanked&&power==4);sync_result=5;
 bad_ref=1;assert(tegra_fb_wingray_dc_blank(0,&fb)==-EIO&&fb.dc_blanked&&power==4);bad_ref=0;
 on_error=-EIO;assert(tegra_fb_wingray_dc_blank(0,&fb)==-EIO&&fb.dc_blanked&&power==4);on_error=0;
 assert(!tegra_fb_wingray_dc_blank(0,&fb)&&!fb.dc_blanked&&dc.enabled);
 fb.legacy_poisoned=true;assert(tegra_fb_wingray_dc_blank(4,&fb)==-EIO);fb.legacy_poisoned=false;
 missing=1;assert(tegra_fb_wingray_dc_blank(4,&fb)==-EINVAL);missing=0;
 for(int j=0;j<3;j++)windows[j].flags=0;
 assert(tegra_fb_wingray_dc_blank(4,&fb)==-ENODATA&&dc.enabled);
 assert(!locked&&update_count>=20);return 0;
}
''')
legacy = (K / 'drivers/staging/tegra/video/fb_legacy.h').read_text()
flip = function(legacy, 'tegra_fb_legacy_flip')
assert flip.index('if (fb->dc_blanked)') < flip.index('tegra_fb_legacy_pin(')
assert 'return -EBUSY;' in flip
baseline = (K / 'arch/arm/configs/wingray_android44_displaypm_defconfig').read_text()
assert 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y' not in baseline
candidate = (K / 'arch/arm/configs/wingray_android44_displaydc_defconfig').read_text()
assert candidate.replace('\nCONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n', '') == baseline
print('PASS actual native-mode round trip, all-window restore, 20 software cycles, failures/retry and baseline isolation; hardware unverified')
