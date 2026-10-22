#!/usr/bin/env python3
"""Exercise actual framebuffer bounds and drawing with guard bytes; no device."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#define DISPLAY_PATTERN_TEST
'''
main=r'''
int main(void) {
 struct fb_var_screeninfo v={0}; struct fb_fix_screeninfo f={0};
 v.xres=1280;v.yres=800;v.xres_virtual=1280;v.yres_virtual=800;v.bits_per_pixel=32;
 v.red.length=v.green.length=v.blue.length=8;v.red.offset=16;v.green.offset=8;
 f.type=FB_TYPE_PACKED_PIXELS;f.visual=FB_VISUAL_TRUECOLOR;f.line_length=5120;f.smem_len=4096000;f.smem_start=0x10000000;
 assert(layout_ok(&v,&f));
 struct fb_var_screeninfo good=v;struct fb_fix_screeninfo fixed=f;
 for(int which=0;which<21;++which) {
  v=good;f=fixed;
  switch(which) {
   case 0:v.xres=1279;break;case 1:v.yres=801;break;
   case 2:v.bits_per_pixel=16;break;case 3:v.xres_virtual=~0U;break;
   case 4:v.yres_virtual=~0U;break;case 5:v.xoffset=~0U;break;
   case 6:v.yoffset=~0U;break;case 7:f.line_length=~0U;break;
   case 8:f.smem_len--;break;case 9:f.smem_len=~0U;break;
   case 10:f.smem_start++;break;case 11:f.mmio_len=4096;break;
   case 12:f.type=1;break;case 13:f.visual=FB_VISUAL_DIRECTCOLOR;break;
   case 14:v.red.offset=32;break;case 15:v.blue.offset=8;break;
   case 16:v.green.length=6;break;case 17:v.blue.msb_right=1;break;
   case 18:v.transp.length=8;v.transp.offset=16;break;
   case 19:v.vmode=FB_VMODE_INTERLACED;break;case 20:v.nonstd=1;break;
  }
  assert(!layout_ok(&v,&f));
 }
 for(int swapped=0;swapped<2;++swapped) {
  v=good;f=fixed;v.red.offset=swapped?0:16;v.blue.offset=swapped?16:0;
  v.transp.length=8;v.transp.offset=24;
  v.xres_virtual=1296;v.yres_virtual=802;v.xoffset=8;v.yoffset=1;
  f.line_length=5248;f.smem_len=f.line_length*v.yres_virtual;
  assert(layout_ok(&v,&f));
  unsigned char *p=malloc(f.smem_len+128);assert(p);memset(p,0x5a,f.smem_len+128);
  draw_pattern(p+64,&v,&f);
  for(unsigned i=0;i<f.smem_len+128;++i) {
   if(i<64||i>=64+f.smem_len) {assert(p[i]==0x5a);continue;}
   unsigned row=(i-64)/f.line_length,col=(i-64)%f.line_length;
   if(row<v.yoffset||row>=v.yoffset+800||col<v.xoffset*4||col>=(v.xoffset+1280)*4)assert(p[i]==0x5a);
  }
  unsigned int *r=(unsigned int *)(p+64+f.line_length+32);
  assert(r[0]==0xffffffffU);
  assert(r[800]==((255U<<v.red.offset)|0xff000000U));
  assert(r[1120]==0xff000000U);
  free(p);
 }
 puts("PASS actual layout/draw: 21 malformed layouts denied; both RGB orders; alpha, offsets, stride and guard bytes verified.");
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-display-test-') as temp:
 p=Path(temp);(p/'test.c').write_text(fixture+(root/'diagnostic/display-pattern.c').read_text()+main)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
