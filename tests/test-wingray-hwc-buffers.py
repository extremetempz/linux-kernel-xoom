#!/usr/bin/env python3
"""Fault-test actual Motorola HWC translation allocation/call-site functions.

Substitute allocator, layer-copy and HAL providers only. This is not a complete
Android HAL build or a fence/rendering compatibility test.
"""
from pathlib import Path
import resource
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
TREE=ROOT/'sources/device-wingray'
PATH='hwc/hwc_tegra2.cpp'


def function(s,name):
    at=s.index(name+'(');start=s.rfind('\nstatic ',0,at)+1
    brace=s.index('{',at);end=brace+1;depth=1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]


PREFIX=r'''
#include <cassert>
#include <climits>
#include <cstddef>
#include <cstdlib>
#include <cerrno>
struct hwc_layer_t {char data[32];};
struct hwc_layer_list_t {unsigned flags;size_t numHwLayers;hwc_layer_t hwLayers[0];};
struct layer1 {int acquireFenceFd,releaseFenceFd;};
struct hwc_display_contents_1_t {void *dpy,*sur;size_t numHwLayers;int retireFenceFd;layer1 hwLayers[2];};
struct hwc_composer_device_1 {int unused;};
typedef hwc_composer_device_1 hwc_composer_device_1_t;
struct org_t {int (*set)(org_t*,void*,void*,hwc_layer_list_t*);
              int (*prepare)(org_t*,hwc_layer_list_t*);};
struct tegra2_hwc_composer_device_1_t {hwc_composer_device_1 base;org_t *org;
 void *prepare_xlatebuf;int prepare_xlatebufsz;void *set_xlatebuf;int set_xlatebufsz;bool fbblanked;};
static bool allocation_fail;
static int alloc_calls,prepare_calls,set_calls,copy_calls,closed,hal_error;
static void *xrealloc(void *p,size_t n){++alloc_calls;return allocation_fail?NULL:std::realloc(p,n);}
static void *xmalloc(size_t n){return xrealloc(NULL,n);}
static int xclose(int fd){assert(fd==3);++closed;return 0;}
static int legacy_prepare(org_t*,hwc_layer_list_t *l){assert(l&&l->numHwLayers==2);++prepare_calls;return 0;}
static int legacy_set(org_t*,void*,void*,hwc_layer_list_t *l){assert(l&&l->numHwLayers==2);++set_calls;return hal_error;}
static void copy_display_contents_1_to_layer_list(hwc_layer_list_t *l,hwc_display_contents_1_t *c){
 assert(l&&c->numHwLayers==2);++copy_calls;l->numHwLayers=c->numHwLayers;}
static void copy_layer_list_to_display_contents_1(hwc_display_contents_1_t*,hwc_layer_list_t *l){assert(l);++copy_calls;}
#define realloc xrealloc
#define malloc xmalloc
#define close xclose
#define ALOGV(...) ((void)0)
'''
MAIN=r'''
int main(){
 org_t org={legacy_set,legacy_prepare};tegra2_hwc_composer_device_1_t dev={};dev.org=&org;
 hwc_display_contents_1_t c={};c.dpy=(void*)1;c.sur=(void*)2;c.numHwLayers=2;
 c.hwLayers[0].acquireFenceFd=3;c.hwLayers[1].acquireFenceFd=-1;
 hwc_display_contents_1_t *displays[]={&c};
 allocation_fail=true;
 assert(tegra2_prepare(&dev.base,1,displays)==-ENOMEM);
 assert(!dev.prepare_xlatebuf&&!dev.prepare_xlatebufsz&&!copy_calls&&!prepare_calls);
 assert(tegra2_set(&dev.base,1,displays)==-ENOMEM);
 assert(!dev.set_xlatebuf&&!dev.set_xlatebufsz&&!copy_calls&&!set_calls&&closed==1);
 assert(c.hwLayers[0].acquireFenceFd==-1&&c.retireFenceFd==-1);
 c.hwLayers[0].acquireFenceFd=3;
 allocation_fail=false;
 assert(tegra2_prepare(&dev.base,1,displays)==0);
 assert(tegra2_set(&dev.base,1,displays)==0);
 assert(dev.prepare_xlatebuf!=dev.set_xlatebuf&&prepare_calls==1&&set_calls==1&&closed==2);
 assert(c.hwLayers[0].acquireFenceFd==-1&&c.hwLayers[0].releaseFenceFd==-1);
 void *old=dev.prepare_xlatebuf;int capacity=dev.prepare_xlatebufsz;
 allocation_fail=true;dev.prepare_xlatebufsz=1;
 assert(tegra2_prepare(&dev.base,1,displays)==-ENOMEM);
 assert(dev.prepare_xlatebuf==old&&dev.prepare_xlatebufsz==1&&prepare_calls==1);
 dev.prepare_xlatebufsz=capacity;
 void *old_set=dev.set_xlatebuf;int set_capacity=dev.set_xlatebufsz;dev.set_xlatebufsz=1;
 assert(tegra2_set(&dev.base,1,displays)==-ENOMEM);
 assert(dev.set_xlatebuf==old_set&&dev.set_xlatebufsz==1&&set_calls==1);
 dev.set_xlatebufsz=set_capacity;
 c.numHwLayers=(size_t)-1;int calls=alloc_calls;
 assert(tegra2_prepare(&dev.base,1,displays)==-EOVERFLOW);
 assert(tegra2_set(&dev.base,1,displays)==-EOVERFLOW);
 assert(alloc_calls==calls&&prepare_calls==1&&set_calls==1);
 c.numHwLayers=2;c.hwLayers[0].acquireFenceFd=3;dev.fbblanked=true;
 assert(tegra2_set(&dev.base,1,displays)==-ENODEV&&closed==3&&set_calls==1);
 dev.fbblanked=false;c.hwLayers[0].acquireFenceFd=3;c.sur=NULL;
 assert(tegra2_set(&dev.base,1,displays)==0&&closed==4&&set_calls==1);
 c.sur=(void*)2;c.hwLayers[0].acquireFenceFd=3;hal_error=-EIO;
 assert(tegra2_set(&dev.base,1,displays)==-EIO&&closed==5&&set_calls==2);
 assert(c.hwLayers[0].acquireFenceFd==-1&&c.retireFenceFd==-1);
 std::free(dev.prepare_xlatebuf);std::free(dev.set_xlatebuf);
 return 0;
}
'''


def run(source,path):
    names=(['release_acquire_fences'] if 'static void release_acquire_fences(' in source else [])+['ensure_xlatebuf','tegra2_set','tegra2_prepare'] if 'static int ensure_xlatebuf(' in source else ['tegra2_set','tegra2_prepare']
    cpp=path.with_suffix('.cpp');cpp.write_text(PREFIX+'\n'.join(function(source,x) for x in names)+MAIN)
    subprocess.run(['c++','-std=gnu++11','-O2','-Wall','-Wextra','-Werror',
                    '-Wno-unused-function',str(cpp),'-o',str(path)],check=True)
    return subprocess.run([str(path)],capture_output=True,
        preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))


with tempfile.TemporaryDirectory(prefix='xoom-hwc-bounds-') as t:
    p=Path(t);result=run((TREE/PATH).read_text(),p/'current')
    assert result.returncode==0,result.stderr.decode()
    old=subprocess.check_output(['git','-C',str(TREE),'show','057937ec:'+PATH],text=True)
    result=run(old,p/'before')
    assert result.returncode!=0 and b'Assertion' in result.stderr,result.stderr.decode()
    prior=subprocess.check_output(['git','-C',str(TREE),'show','c7b7b055:'+PATH],text=True)
    result=run(prior,p/'before-fence-cleanup')
    assert result.returncode!=0 and b'Assertion' in result.stderr,result.stderr.decode()
print('PASS actual HWC bounds plus acquire-fd cleanup on allocation, blanking, missing-surface and legacy-HAL errors. Both previous versions fail negative controls. Not a full HAL/fence-ordering validation.')
