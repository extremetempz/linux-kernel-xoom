#!/usr/bin/env python3
"""Fault-test actual T20/T30 context-handler allocation; no GPU command replay."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
def extract(version):
 s=(root/f'sources/kernel-donor/drivers/staging/tegra/video/host/gr3d/gr3d_{version}.c').read_text()
 a=s.index('struct nvhost_hwctx_handler *nvhost_gr3d_'+version+'_ctxhandler_init(');e=s.index('{',a)+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
prefix=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
#define GFP_KERNEL 0
#define IS_ERR_OR_NULL(p) (!(p)||(uintptr_t)(p)>=(uintptr_t)-4095)
#define IS_ERR_VALUE(v) ((uintptr_t)(v)>=(uintptr_t)-4095)
#define mem_mgr_flag_write_combine 1
struct mem_mgr{int unused;};struct mem_handle{int unused;};
struct nvhost_channel;struct nvhost_hwctx_handler{void(*destroy)(struct nvhost_hwctx_handler*,struct nvhost_channel*);void(*alloc)(void);void(*save_push)(void);void(*save_service)(void);void(*get)(void);void(*put)(void);};
struct host1x_hwctx_handler{struct nvhost_hwctx_handler h;u32 syncpt,waitbase,save_size,save_slots;struct mem_handle*save_buf;uintptr_t save_phys;};
struct nvhost_channel{void*dev;};
static struct mem_mgr manager;static struct{struct mem_mgr*memmgr;}host={&manager};
#define nvhost_get_host(d) ((void)(d),&host)
static int fail,stage,handlers,buffers,mappings,pins,writes,null_buffer;
static u32 mapped[16];static struct mem_handle buffer;
static int step(void){return ++stage==fail;}
static void*kmalloc(size_t n,int flags){(void)flags;if(step())return NULL;handlers++;return malloc(n);}
static void kfree(void*p){assert(handlers==1&&!buffers&&!mappings&&!pins);handlers--;free(p);}
static struct mem_handle*alloc_(struct mem_mgr*m,size_t n,int a,int f){assert(m==&manager&&n==16&&a==32&&f==1);if(step())return null_buffer?NULL:(void*)(intptr_t)-ENOMEM;buffers++;return &buffer;}
static void*mmap_(struct mem_handle*b){assert(b==&buffer&&buffers==1);if(step())return NULL;mappings++;return mapped;}
static uintptr_t pin_(struct mem_mgr*m,struct mem_handle*b){assert(m==&manager&&b==&buffer&&mappings==1);if(step())return (uintptr_t)-EIO;pins++;return 0x200000;}
static void munmap_(struct mem_handle*b,void*p){assert(b==&buffer&&p==mapped&&mappings==1);mappings--;}
static void put_(struct mem_mgr*m,struct mem_handle*b){assert(m==&manager&&b==&buffer&&buffers==1&&!mappings&&!pins);buffers--;}
static void unpin_(struct mem_mgr*m,struct mem_handle*b){assert(m==&manager&&b==&buffer&&pins==1&&!mappings);pins--;}
static struct{struct mem_handle*(*alloc)(struct mem_mgr*,size_t,int,int);void*(*mmap)(struct mem_handle*);uintptr_t(*pin)(struct mem_mgr*,struct mem_handle*);void(*munmap)(struct mem_handle*,void*);void(*put)(struct mem_mgr*,struct mem_handle*);void(*unpin)(struct mem_mgr*,struct mem_handle*);}ops={alloc_,mmap_,pin_,munmap_,put_,unpin_};
#define mem_op() ops
#define to_host1x_hwctx_handler(h) ((struct host1x_hwctx_handler*)(h))
void nvhost_3dctx_handler_free(struct nvhost_hwctx_handler*,struct nvhost_channel*);
static void setup_save(struct host1x_hwctx_handler*p,u32*ptr){if(!ptr)p->save_size=4;else{assert(ptr==mapped&&mappings==1&&pins==1);writes++;}}
static void ctx3d_alloc_v0(void){}static void ctx3d_alloc_v1(void){}
static void save_push_v0(void){}static void save_push_v1(void){}
static void ctx3d_save_service(void){}static void nvhost_3dctx_get(void){}static void nvhost_3dctx_put(void){}
'''
main=r'''
int main(void){struct nvhost_channel ch={0};
 struct nvhost_hwctx_handler*(*init[])(u32,u32,struct nvhost_channel*)={nvhost_gr3d_t20_ctxhandler_init,nvhost_gr3d_t30_ctxhandler_init};
 for(int v=0;v<2;v++){
  for(fail=1;fail<=4;fail++){
   stage=writes=0;assert(!init[v](22,1,&ch));assert(!handlers&&!buffers&&!mappings&&!pins&&!writes);
  }
  fail=2;stage=0;null_buffer=1;assert(!init[v](22,1,&ch));assert(!handlers&&!buffers);null_buffer=0;
  fail=stage=writes=0;struct nvhost_hwctx_handler*h=init[v](22,1,&ch);
  assert(h&&handlers==1&&buffers==1&&!mappings&&pins==1&&writes==1);
  assert(h->destroy);h->destroy(h,&ch);assert(!handlers&&!buffers&&!pins&&!mappings);
 }
 puts("PASS actual T20/T30 handlers: allocation, mapping and pin failures unwind; save data written only after pin; successful temporary mapping released (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as t:
 common=(root/'sources/kernel-donor/drivers/staging/tegra/video/host/gr3d/gr3d.c').read_text()
 a=common.index('void nvhost_3dctx_handler_free(');e=common.index('\nvoid nvhost_3dctx_get(',a)
 p=Path(t)/'test.c';p.write_text(prefix+common[a:e]+extract('t20')+extract('t30')+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
