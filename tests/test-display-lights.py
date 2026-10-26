#!/usr/bin/env python3
"""Execute the actual KitKat lights adapter with faulted file operations."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'android/lights/lights.c'
code=r'''
#define XOOM_LIGHTS_TEST
#include <assert.h>
#include <string.h>
#include "lights.c"
static int opened,closed,written,open_error,write_error,close_error,short_write,interrupt_once;
static char last[8];
static int blanks,blank_mode,ioctl_error;
int xoom_open(const char *path,int flags){assert(!strcmp(path,"/sys/class/backlight/lcd-backlight/brightness")||!strcmp(path,"/dev/graphics/fb0"));assert(flags==(1|02000000)||flags==(2|02000000));opened++;return open_error?open_error:4;}
int xoom_write(int fd,const void *p,unsigned int n){assert(fd==4&&n<=4);written++;if(interrupt_once){interrupt_once=0;return -4;}if(write_error)return write_error;memcpy(last,p,n);last[n]=0;return short_write?(int)n-1:(int)n;}
int xoom_ioctl(int fd,unsigned int cmd,unsigned int arg){assert(fd==4&&cmd==0x4611);blanks++;blank_mode=arg;return ioctl_error;}
int xoom_close(int fd){assert(fd==4);closed++;return close_error;}
int main(void){struct hw_device_t *d=0;struct light_device_t *bl;struct light_state_t s={0};
 assert(HMI.tag==HARDWARE_MODULE_TAG&&!strcmp(HMI.id,"lights"));
 assert(open_light(&HMI,"foo",&d)==-38&&!d&&!opened);
 assert(open_light(&HMI,"notifications",&d)==0&&d);
 assert(!set_backlight((struct light_device_t*)d,&s)&&!opened&&!written&&!blanks);
 assert(open_light(&HMI,"backlight",&d)==0&&d&&d->module==&HMI);
 bl=(struct light_device_t*)d;
 assert(!bl->set_light(bl,&s)&&!strcmp(last,"0\n")&&blanks==1&&blank_mode==4);
 s.color=0xffffffff;assert(!bl->set_light(bl,&s)&&!strcmp(last,"255\n")&&blanks==2&&blank_mode==0);
 s.color=0x00808080;assert(!bl->set_light(bl,&s)&&!strcmp(last,"128\n"));
 s.color=0x00ff0000;assert(!bl->set_light(bl,&s)&&!strcmp(last,"76\n"));
 assert(bl->set_light(bl,0)==-22);
 int prev=closed;open_error=-13;assert(bl->set_light(bl,&s)==-13&&closed==prev);
 open_error=0;write_error=-5;assert(bl->set_light(bl,&s)==-5&&closed==prev+1);
 write_error=0;short_write=1;assert(bl->set_light(bl,&s)==-5);
 short_write=0;interrupt_once=1;assert(!bl->set_light(bl,&s));
 close_error=-5;assert(bl->set_light(bl,&s)==-5);close_error=0;
 s.color=0;ioctl_error=-5;assert(bl->set_light(bl,&s)==-5&&!display_blanked);
 ioctl_error=0;assert(!bl->set_light(bl,&s)&&display_blanked);
 s.color=0xffffffff;ioctl_error=-5;prev=written;assert(bl->set_light(bl,&s)==-5&&display_blanked&&written==prev);
 return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-I',str(source.parent),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual lights HAL: ABI metadata, fixed backlight path, black/white/RGB, denied/short/error/EINTR IO; fixed fb0 blank/unblank ordering and errors; no charger/notification actions')
