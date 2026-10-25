#!/usr/bin/env python3
"""Exercise actual optional framebuffer compatibility code with provider faults.

Provider stubs do not validate display hardware, concurrency or DMA/cache
behavior. Actual ARM builds and original-header ABI comparison are separate.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / 'sources/kernel-donor'
header = (TREE / 'drivers/staging/tegra/include/video/tegrafb.h').read_text()
header = re.sub(r'^#include.*\n', '', header, flags=re.M)
code = (TREE / 'drivers/staging/tegra/video/fb_legacy.h').read_text()
fb_source = (TREE / 'drivers/staging/tegra/video/fb.c').read_text()


def function(name):
    start = fb_source.index(name + '(')
    start = fb_source.rfind('\n', 0, start) + 1
    end = fb_source.index('\n}', start) + 2
    return fb_source[start:end]

PRELUDE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#include <sys/ioctl.h>
typedef uint32_t u32,__u32,phys_addr_t;
typedef int32_t __s32;
typedef uint64_t u64;
#define CONFIG_FB_TEGRA_WINGRAY_LEGACY 1
#define __user
#define GFP_KERNEL 0
#define EPROBE_DEFER 517
#define BUILD_BUG_ON(x) _Static_assert(!(x),"ABI")
#define BIT(x) (1U<<(x))
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
#define IS_ERR_VALUE(x) ((u32)(x)>=(u32)-4095)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define dfixed_const(x) ((x)<<12)
#define DC_N_WINDOWS 3
#define TEGRA_WIN_FLAG_ENABLED 1
#define TEGRA_WIN_FLAG_BLEND_PREMULT 2
#define TEGRA_WIN_FLAG_BLEND_COVERAGE 4
#define TEGRA_WIN_FLAG_INVERT_H 8
#define TEGRA_WIN_FLAG_INVERT_V 16
struct mutex {int held;};
static void mutex_init(struct mutex *m) {m->held=0;}
static void mutex_lock(struct mutex *m) {assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m) {assert(m->held);m->held=0;}
struct nvmap_handle {struct mutex lock;bool alloc,secure;u32 orig_size;};
struct nvmap_handle_ref {struct nvmap_handle *handle;int pinned;unsigned id;};
struct nvmap_client {int refs;};
static struct nvmap_client *nvmap_dev;
struct nvhost_device {int unused;};
struct nvhost_master {int syncpt;};
struct tegra_dc;
struct tegra_dc_win {
 struct tegra_dc *dc;
 unsigned idx,flags,fmt,z,global_alpha;
 struct {u32 full;} x,y,w,h;
 u32 out_x,out_y,out_w,out_h,phys_addr,phys_addr_u,phys_addr_v,stride,stride_uv;
 void *virt_addr;
 struct nvmap_handle_ref *cur_handle;
};
struct tegra_dc {struct {u32 h_active,v_active;} mode;bool enabled;struct tegra_dc_win wins[3];};
struct tegra_fb_info {
 struct fb_info *info;
 struct tegra_dc_win *win;struct nvhost_device *ndev;
 struct mutex legacy_lock;
 bool legacy_enabled,legacy_dead,legacy_open,legacy_poisoned;
 struct nvmap_client *user_nvmap,*fb_nvmap;
 struct nvmap_handle_ref *legacy_front[3],*legacy_pending[3];
};
struct fb_info {void *par,*screen_base;struct mutex lock;};
static int fb_refs,info_freed,mapping_unmapped;
static void tegra_fb_legacy_fb_destroy(struct fb_info *info);
static void unregister_framebuffer(struct fb_info *info){assert(--fb_refs>=0);if(!fb_refs)tegra_fb_legacy_fb_destroy(info);}
static void iounmap(void *ptr){assert(ptr);mapping_unmapped++;}
static void framebuffer_release(struct fb_info *info){assert(info);info_freed++;}
static struct nvmap_client provider,fb_client,user_client;
static struct nvhost_master host;
static struct nvmap_handle handles[8];
static bool wingray,copy_in_bad,copy_out_bad,fail_saved;
static int fail_create;
static int pin_calls,dup_calls,fail_pin,fail_dup,wait_error,update_error,sync_result;
static int live_refs,pins,signals,updates,waits,saved_live;
static u32 sync_value;
static char events[1024];static unsigned events_len;
static void event(char c){assert(events_len<sizeof(events)-1);events[events_len++]=c;events[events_len]=0;}
static bool of_machine_is_compatible(const char *s){assert(!strcmp(s,"motorola,wingray"));return wingray;}
static struct nvmap_client *nvmap_create_client(struct nvmap_client *d,const char *name){
 assert(d==nvmap_dev&&!strcmp(name,"wingray-fb"));if(fail_create==1)return ERR_PTR(-ENOMEM);if(fail_create==2)return NULL;fb_client.refs++;return &fb_client;
}
static struct nvmap_client *nvmap_client_get_file(int fd){if(fd!=7)return ERR_PTR(-EBADF);user_client.refs++;return &user_client;}
static void nvmap_client_put(struct nvmap_client *c){assert(c&&c->refs>0);c->refs--;}
static struct nvmap_handle *nvmap_get_handle_id(struct nvmap_client *c,u32 id){assert(c);return id&&id<8?&handles[id]:NULL;}
static void nvmap_handle_put(struct nvmap_handle *h){assert(h);}
static struct nvmap_handle_ref *nvmap_duplicate_handle_id(struct nvmap_client *c,u32 id){
 struct nvmap_handle_ref *r;assert(c&&id&&id<8);if(++dup_calls==fail_dup)return ERR_PTR(-ENOMEM);
 r=calloc(1,sizeof(*r));assert(r);r->handle=&handles[id];r->id=id;live_refs++;return r;
}
static phys_addr_t nvmap_pin(struct nvmap_client *c,struct nvmap_handle_ref *r){
 assert(c);if(++pin_calls==fail_pin)return (u32)-ENOMEM;assert(!r->pinned);r->pinned=1;pins++;event('P');return 0x30000000+r->id*0x800000;
}
static void nvmap_unpin(struct nvmap_client *c,struct nvmap_handle_ref *r){assert(c&&r->pinned==1);r->pinned=0;pins--;event('N');}
static void nvmap_free(struct nvmap_client *c,struct nvmap_handle_ref *r){assert(c&&r&&!r->pinned);free(r);live_refs--;event('F');}
static struct nvhost_master *nvhost_get_host(struct nvhost_device *d){assert(d);return &host;}
static int nvhost_syncpt_is_valid(int *sp,u32 id){assert(sp==&host.syncpt);return id<32;}
static int nvhost_syncpt_wait_timeout_ext(struct nvhost_device *d,u32 id,u32 val,u32 timeout,u32 *out){
 assert(d&&id<32&&timeout==500&&!out);(void)val;waits++;event('W');return wait_error;
}
static u32 msecs_to_jiffies(u32 ms){return ms;}
static struct tegra_dc_win *tegra_dc_get_window(struct tegra_dc *dc,int idx){return idx>=0&&idx<3?&dc->wins[idx]:NULL;}
static int tegra_dc_update_windows(struct tegra_dc_win **wins,int n){assert(n>0&&n<=3&&wins[0]);updates++;event('U');return update_error;}
static int tegra_dc_sync_windows(struct tegra_dc_win **wins,int n){assert(n>0&&n<=3&&wins[0]);event('S');return sync_result;}
static u32 tegra_dc_incr_syncpt_max(struct tegra_dc *dc,int i){assert(dc&&!i);event('M');return ++sync_value;}
static u32 tegra_dc_get_syncpt_id(struct tegra_dc *dc,int i){assert(dc&&!i);return 22;}
static void tegra_dc_incr_syncpt_min(struct tegra_dc *dc,int i,u32 v){assert(dc&&!i&&v==sync_value);signals++;event('C');}
static void tegra_dc_disable(struct tegra_dc *dc){dc->enabled=false;event('D');}
static int copy_from_user(void *to,const void *from,unsigned long n){if(copy_in_bad)return 1;memcpy(to,from,n);return 0;}
static int copy_to_user(void *to,const void *from,unsigned long n){if(copy_out_bad)return 1;memcpy(to,from,n);return 0;}
static void *kcalloc(unsigned n,unsigned long size,int flags){void *p;(void)flags;if(fail_saved)return NULL;p=calloc(n,size);assert(p);saved_live++;return p;}
static void kfree(void *p){assert(p);free(p);saved_live--;}
'''

MAIN = r'''
static struct tegra_fb_info fb;
static struct fb_info info;
static struct tegra_dc dc;
static struct nvhost_device ndev;
static void start(void){
 unsigned i;int fd=7;
 assert(!live_refs&&!pins&&!saved_live&&!fb_client.refs&&!user_client.refs);
 memset(&fb,0,sizeof(fb));memset(&dc,0,sizeof(dc));memset(handles,0,sizeof(handles));
 dc.mode.h_active=1280;dc.mode.v_active=800;dc.enabled=true;
 for(i=0;i<3;i++){dc.wins[i].dc=&dc;dc.wins[i].idx=i;}
 for(i=1;i<8;i++){handles[i].alloc=true;handles[i].orig_size=4096000;}
 fb.win=&dc.wins[0];fb.ndev=&ndev;info.par=&fb;fb.info=&info;
 info.screen_base=(void *)0x1234;info.lock.held=0;fb_refs=2;info_freed=mapping_unmapped=0;
 wingray=true;nvmap_dev=&provider;fail_create=copy_in_bad=copy_out_bad=fail_saved=false;
 pin_calls=dup_calls=fail_pin=fail_dup=wait_error=update_error=signals=updates=waits=0;
 sync_result=1;events_len=0;events[0]=0;
 assert(!tegra_fb_legacy_init(&fb));assert(!tegra_fb_legacy_open(&info,1));
 assert(!tegra_fb_legacy_ioctl(&fb,FBIO_TEGRA_SET_NVMAP_FD,(unsigned long)&fd));
}
static struct tegra_fb_flip_args request(int count){
 struct tegra_fb_flip_args args={0};int i;
 for(i=0;i<3;i++)args.win[i].index=-1;
 for(i=0;i<count;i++)args.win[i]=(struct tegra_fb_windowattr){
 .index=i,.buff_id=i+1,.pixformat=TEGRA_FB_WIN_FMT_R8G8B8A8,
 .stride=5120,.w=1280,.h=800,.out_w=1280,.out_h=800,.z=i,.pre_syncpt_id=(u32)-1};
 return args;
}
static int flip(struct tegra_fb_flip_args *a){return tegra_fb_legacy_ioctl(&fb,FBIO_TEGRA_FLIP,(unsigned long)a);}
static void finish(void){
 assert(!tegra_fb_legacy_release(&info,1));
 tegra_fb_legacy_destroy(&fb);assert(tegra_fb_legacy_dead(&fb));
 assert(!live_refs&&!pins&&!saved_live&&!fb_client.refs&&!user_client.refs);
}
int main(void){
 struct tegra_fb_flip_args a;struct nvmap_handle_ref *old;unsigned i;int fd;
 start();assert(tegra_fb_legacy_open(&info,1)==-EBUSY);a=request(3);
 assert(!flip(&a));assert(pins==3&&signals==1&&a.post_syncpt_id==22&&a.post_syncpt_val==1);
 assert(strstr(events,"USMC"));assert(tegra_fb_legacy_busy(&fb));
 for(i=0;i<3;i++){assert(dc.wins[i].w.full==(1280U<<12));assert(fb.legacy_front[i]);}
 events_len=0;events[0]=0;assert(!flip(&a));assert(pins==3&&signals==2);
 assert(strstr(events,"USMCNF"));
 a=request(1);a.win[0].buff_id=0;assert(!flip(&a));assert(pins==2&&!dc.wins[0].flags);finish();

 start();a=request(1);a.win[0].index=-2;assert(flip(&a)==-EINVAL&&!pin_calls);finish();
 start();a=request(1);a.win[0].index=3;assert(flip(&a)==-EINVAL&&!pin_calls);finish();
 start();a=request(2);a.win[1].index=0;assert(flip(&a)==-EINVAL&&!pin_calls);finish();
 start();a=request(0);assert(flip(&a)==-EINVAL&&!pin_calls);finish();
 start();a=request(1);a.win[0].pre_syncpt_id=32;assert(flip(&a)==-EINVAL&&!pin_calls);finish();
 for(i=1;i<=3;i++){
  start();a=request(3);fail_pin=i;assert(flip(&a)==-ENOMEM&&!pins&&!live_refs&&!updates);finish();
  start();a=request(3);fail_dup=i;assert(flip(&a)==-ENOMEM&&!pins&&!live_refs&&!updates);finish();
 }
 start();a=request(1);a.win[0].buff_id=99;assert(flip(&a)==-EPERM&&!pins);finish();
 start();a=request(1);handles[1].secure=true;assert(flip(&a)==-EPERM&&!pins);finish();
 start();a=request(1);handles[1].alloc=false;assert(flip(&a)==-EPERM&&!pins);finish();
 start();a=request(1);fail_saved=true;assert(flip(&a)==-ENOMEM&&!dup_calls);finish();
 start();a=request(3);a.win[2].pre_syncpt_id=2;wait_error=-ETIMEDOUT;
 assert(flip(&a)==-ETIMEDOUT&&waits==1&&!updates&&!signals&&!pins);finish();
 start();a=request(1);assert(!flip(&a));old=fb.legacy_front[0];
 update_error=-EFAULT;assert(flip(&a)==-EFAULT&&pins==1&&fb.legacy_front[0]==old&&dc.wins[0].cur_handle==old);finish();
 for(i=0;i<2;i++){
  start();a=request(1);assert(!flip(&a));old=fb.legacy_front[0];signals=0;
  sync_result=i?-EINTR:0;assert(flip(&a)==(i?-EINTR:-ETIMEDOUT));
  assert(fb.legacy_poisoned&&fb.legacy_front[0]==old&&pins==2&&!signals);
  assert(flip(&a)==-EIO);events_len=0;events[0]=0;finish();assert(events[0]=='D');
 }
 start();a=request(1);copy_in_bad=true;assert(flip(&a)==-EFAULT&&!pins);copy_in_bad=false;finish();
 start();a=request(1);copy_out_bad=true;assert(flip(&a)==-EFAULT&&pins==1&&signals==1);copy_out_bad=false;finish();
 start();fd=-1;assert(tegra_fb_legacy_ioctl(&fb,FBIO_TEGRA_SET_NVMAP_FD,(unsigned long)&fd)==-EINVAL);
 fd=8;assert(tegra_fb_legacy_ioctl(&fb,FBIO_TEGRA_SET_NVMAP_FD,(unsigned long)&fd)==-EBADF);finish();
 start();a=request(1);assert(!flip(&a));assert(!tegra_fb_legacy_release(&info,1)&&pins==1);
 assert(!tegra_fb_legacy_open(&info,1));fd=7;assert(!tegra_fb_legacy_ioctl(&fb,FBIO_TEGRA_SET_NVMAP_FD,(unsigned long)&fd));
 assert(!flip(&a)&&pins==1);finish();

 /* Actual extent/conversion policy: exact last byte passes, one byte short
  * and all unsupported layouts/overflows fail. */
 start();a=request(1);
 assert(!tegra_fb_legacy_validate(&a.win[0],4096000,0x30000000,1280,800));
 assert(tegra_fb_legacy_validate(&a.win[0],4095999,0x30000000,1280,800)==-EINVAL);
 assert(tegra_fb_legacy_validate(&a.win[0],4096000,0xffffffff,1280,800)==-EINVAL);
 a.win[0].flags=TEGRA_FB_WIN_FLAG_TILED;assert(flip(&a)==-EOPNOTSUPP&&!updates);
 a=request(1);a.win[0].pixformat=TEGRA_FB_WIN_FMT_YUV420P;assert(flip(&a)==-EOPNOTSUPP&&!updates);
 a=request(1);a.win[0].out_w--;assert(flip(&a)==-EOPNOTSUPP&&!updates);
 a=request(1);a.win[0].offset=0xfffffff0;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].x=0xffffffff;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].out_x=0xffffffff;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].stride=5119;assert(flip(&a)==-EINVAL&&!updates);
 for(i=0;i<6;i++){
  static const u32 formats[]={4,5,6,7,12,13};unsigned cpp=i<4?2:4;
  a=request(1);a.win[0].pixformat=formats[i];a.win[0].stride=1280*cpp;
  a.win[0].flags=TEGRA_FB_WIN_FLAG_INVERT_H|TEGRA_FB_WIN_FLAG_INVERT_V;
  assert(!tegra_fb_legacy_validate(&a.win[0],1280*800*cpp,0x30000000,1280,800));
  assert(tegra_fb_legacy_validate(&a.win[0],1280*800*cpp-1,0x30000000,1280,800)==-EINVAL);
 }
 a=request(1);a.win[0].x=1;a.win[0].w=a.win[0].out_w=1279;
 assert(!tegra_fb_legacy_validate(&a.win[0],4096000,0x30000000,1280,800));
 a=request(1);a.win[0].offset_u=4;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].stride_uv=4;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].blend=3;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].z=3;
 assert(!tegra_fb_legacy_validate(&a.win[0],4096000,0x30000000,1280,800));
 a=request(1);a.win[0].offset=1;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].w=a.win[0].out_w=0;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].h=a.win[0].out_h=0;assert(flip(&a)==-EINVAL&&!updates);
 a=request(1);a.win[0].stride=0x10000;assert(flip(&a)==-EINVAL&&!updates);
 finish();
 for(i=0;i<2;i++){
  start();a=request(1);assert(!flip(&a));
  if(i){sync_result=0;assert(flip(&a)==-ETIMEDOUT&&pins==2);}
  tegra_fb_unregister(&fb);
  assert(fb.legacy_dead&&!pins&&!live_refs&&!info_freed&&!mapping_unmapped&&fb_refs==1);
  fb.win=NULL; /* controller storage may disappear before the file closes */
  assert(tegra_fb_legacy_open(&info,1)==-EIO&&flip(&a)==-EIO);
  assert(!tegra_fb_legacy_release(&info,1));
  if(!--fb_refs)tegra_fb_legacy_fb_destroy(&info);
  assert(info_freed==1&&mapping_unmapped==1&&!fb_client.refs&&!user_client.refs);
 }
 for(i=1;i<=2;i++){
  memset(&fb,0,sizeof(fb));fb.win=&dc.wins[0];fail_create=i;
  assert(tegra_fb_legacy_init(&fb)==-ENOMEM&&!fb.legacy_enabled);
 }
 memset(&fb,0,sizeof(fb));nvmap_dev=NULL;
 assert(tegra_fb_legacy_init(&fb)==-EPROBE_DEFER);
 wingray=false;assert(!tegra_fb_legacy_init(&fb)&&!fb.legacy_enabled);
 assert(!tegra_fb_legacy_open(&info,1));assert(!tegra_fb_legacy_release(&info,1));
 tegra_fb_legacy_destroy(&fb);assert(tegra_fb_legacy_dead(&fb));
 assert(tegra_fb_legacy_open(&info,1)==-EIO);tegra_fb_legacy_destroy(&fb);
 puts("PASS actual Wingray framebuffer compatibility: posting/completion, ownership/unwind, timeouts, retained pins, bounds and fail-closed layouts. HOST PROVIDERS ONLY.");
}
'''

with tempfile.TemporaryDirectory(prefix='xoom-fb-legacy-test-') as temp:
    path = Path(temp) / 'test.c'
    path.write_text(PRELUDE + header + code + '\n' +
                    function('tegra_fb_legacy_fb_destroy') + '\n' +
                    function('tegra_fb_unregister') + '\n' + MAIN)
    binary = Path(temp) / 'test'
    subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', str(path), '-o', str(binary)],
                   check=True)
    subprocess.run([str(binary)], check=True,
                   env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
