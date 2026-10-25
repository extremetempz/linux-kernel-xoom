#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,os
r=Path(__file__).resolve().parents[1]
code='''#include <assert.h>
#define DISPLAY_PATTERN_TEST
#define XOOM_LEGACY_DISPLAY 1
'''+(r/'diagnostic/display-pattern.c').read_text()+'''
int main(void){
 struct fb_var_screeninfo v={0};struct fb_fix_screeninfo f={0};
 v.xres=v.xres_virtual=1280;v.yres=800;v.yres_virtual=1600;v.bits_per_pixel=32;
 v.red.length=v.green.length=v.blue.length=8;v.green.offset=8;v.blue.offset=16;
 v.pixclock=15060;f.type=FB_TYPE_PACKED_PIXELS;f.visual=FB_VISUAL_TRUECOLOR;
 f.line_length=5120;f.smem_start=0x2e800000;f.smem_len=0x800000;
 assert(layout_ok(&v,&f));
 v.pixclock=0;assert(!layout_ok(&v,&f));v.pixclock=15060;
 f.smem_start=0x30000000;assert(!layout_ok(&v,&f));f.smem_start=0x2e800000;
 f.smem_len--;assert(!layout_ok(&v,&f));f.smem_len=0x800000;
 v.yres_virtual=2048;assert(!layout_ok(&v,&f));v.yres_virtual=1600;
 f.mmio_len=4;assert(!layout_ok(&v,&f));f.mmio_len=0;
 v.red.offset=16;assert(!layout_ok(&v,&f));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(code)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
print('PASS actual legacy framebuffer layout: exact Motorola reservation/pixel clock, no MMIO or nvmap heap alias, bounded double buffer')
