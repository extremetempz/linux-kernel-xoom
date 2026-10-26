/* SPDX-License-Identifier: Apache-2.0
 * Minimal KitKat backlight-only adapter. No notification, charger LED,
 * GPIO, voltage or SoC suspend operations. Fixed fb0 blank/unblank only. The kernel owns LP8550.
 */
#include "kitkat_lights_abi.h"
#define BRIGHTNESS_PATH "/sys/class/backlight/lcd-backlight/brightness"
#ifdef XOOM_LIGHTS_TEST
extern int xoom_open(const char *, int);
extern int xoom_write(int, const void *, unsigned int);
extern int xoom_close(int);
extern int xoom_ioctl(int, unsigned int, unsigned int);
#else
/* ARM EABI direct syscalls: no dependency on host or Android libc. */
static int xoom_call(int nr, int a, int b, unsigned int c)
{
 register int r0 __asm__("r0") = a;
 register int r1 __asm__("r1") = b;
 register unsigned int r2 __asm__("r2") = c;
 register int r7 __asm__("r7") = nr;
 __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory", "cc");
 return r0;
}
static int xoom_open(const char *p, int flags) { return xoom_call(5,(int)p,flags,0); }
static int xoom_write(int fd, const void *p, unsigned int n) { return xoom_call(4,fd,(int)p,n); }
static int xoom_close(int fd) { return xoom_call(6,fd,0,0); }
static int xoom_ioctl(int fd,unsigned int cmd,unsigned int arg) { return xoom_call(54,fd,cmd,arg); }
#endif

/* The installed legacy HWC has no established kernel blank contract.
 * Bridge zero/nonzero backlight transitions to the existing fb0 ioctl.
 * Do not post pixels, reopen GPU channels, or restart framework services. */
static int display_blanked;
static int display_power(unsigned int blank)
{
 int fd,ret,closed;
 do { fd=xoom_open("/dev/graphics/fb0",2|02000000); } while(fd==-4);
 if(fd<0)return fd;
 do { ret=xoom_ioctl(fd,0x4611,blank); } while(ret==-4); /* FBIOBLANK */
 closed=xoom_close(fd);
 return ret<0?ret:closed<0?closed:0;
}

static int set_backlight(struct light_device_t *dev, const struct light_state_t *state)
{
 unsigned int r, g, b, value;
 char data[4];
 int fd, ret, close_ret, len=0;
 (void)dev;
 if (!state)
  return -22;
 r=(state->color>>16)&255;g=(state->color>>8)&255;b=state->color&255;
 value=(77*r+150*g+29*b)>>8;
 /* Restore scanout before allowing the light back on. Brightness changes
  * while already on never reprogram the framebuffer window. */
 if(value && display_blanked) {
  ret=display_power(0);
  if(ret)return ret;
  display_blanked=0;
 }
 if (value>=100)
  data[len++]='0'+value/100;
 if (value>=10)
  data[len++]='0'+(value/10)%10;
 data[len++]='0'+value%10;
 data[len++]='\n';
 do { fd=xoom_open(BRIGHTNESS_PATH,1|02000000); } while(fd==-4);
 if (fd<0)
  return fd;
 do { ret=xoom_write(fd,data,len); } while(ret==-4);
 close_ret=xoom_close(fd); /* Never retry close: descriptor may be reused. */
 if (ret<0)
  return ret;
 if (ret!=len)
  return -5;
 if(close_ret<0)return close_ret;
 if(!value && !display_blanked) {
  ret=display_power(4);
  if(ret)return ret;
  display_blanked=1;
 }
 return 0;
}
static int close_light(struct hw_device_t *dev) { (void)dev;return 0; }
static struct light_device_t light = {
 .common={.tag=HARDWARE_DEVICE_TAG,.version=0,.close=close_light},
 .set_light=set_backlight,
};
static int open_light(const struct hw_module_t *module,const char *id,struct hw_device_t **out)
{
 const char *expected="backlight";
 unsigned int i=0;
 if (!module || !id || !out)
  return -22;
 *out=0;
 while(id[i] && expected[i] && id[i]==expected[i])i++;
 if (id[i] || expected[i])
  return -38; /* Explicitly unsupported lights; no false success. */
 light.common.module=(struct hw_module_t *)module;
 *out=&light.common;
 return 0;
}
static struct hw_module_methods_t methods={.open=open_light};
__attribute__((visibility("default"))) struct hw_module_t HMI = {
 .tag=HARDWARE_MODULE_TAG,.module_api_version=0x0100,.hal_api_version=0,
 .id="lights",.name="Wingray P3 LP8550 backlight adapter",
 .author="Xoom port",.methods=&methods,
};
