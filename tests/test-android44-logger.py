#!/usr/bin/env python3
"""Exercise actual logger write path: faults, truncation, wrap and concurrency.

Host kernel APIs are mocked. This does not replace target logger ABI tests.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1];tree=root/'sources/kernel-donor/drivers/staging/android'
s=(tree/'logger.c').read_text()
def extract(signature):
 start=s.index(signature);op=s.index('{',start);end=op+1;depth=1
 while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]+'\n'
actual=extract('static void do_write_log(')+extract('static ssize_t logger_write_iter(')
fixture=r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <sys/types.h>
#include <time.h>
#include "logger.h"
#define GFP_KERNEL 0
#define min(a,b) ((a)<(b)?(a):(b))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define logger_offset(n) ((n)&(log->size-1))
struct logger_log { unsigned char *buffer;size_t size,w_off;pthread_mutex_t mutex;unsigned wq; };
struct kiocb { struct logger_log *ki_filp; };
struct iov_iter { const unsigned char *data;size_t count,pos;bool fault; };
static _Thread_local bool held;
static bool fail_alloc;static _Atomic unsigned allocs;
static struct { int tgid,pid; } task={123,456};
#define current (&task)
static size_t iov_iter_count(struct iov_iter *p) {return p->count;}
static void *kmalloc(size_t n,int g) {(void)g;atomic_fetch_add(&allocs,1);return fail_alloc?NULL:malloc(n);}
static void kfree(void *p) {free(p);}
static size_t copy_from_iter(void *dest,size_t n,struct iov_iter *p) {if(p->fault)--n;memcpy(dest,p->data+p->pos,n);p->pos+=n;return n;}
static struct timespec current_kernel_time(void) {struct timespec t={100,200};return t;}
static void *current_user_ns(void) {return NULL;}
static unsigned current_euid(void) {return 1000;}
static unsigned from_kuid_munged(void *p,unsigned u) {(void)p;return u;}
static struct logger_log *file_get_log(struct logger_log *p) {return p;}
static void mutex_lock(pthread_mutex_t *m) {assert(!held);assert(!pthread_mutex_lock(m));held=true;}
static void mutex_unlock(pthread_mutex_t *m) {assert(held);held=false;assert(!pthread_mutex_unlock(m));}
static void fix_up_readers(struct logger_log *p,size_t n) {assert(held&&n<=p->size);}
static void wake_up_interruptible(unsigned *p) {(void)p;}
'''
main=r'''
static struct logger_log logbuf;
static void *writer(void *arg) {
 unsigned char data[80];memset(data,(int)(uintptr_t)arg,sizeof(data));
 struct kiocb io={&logbuf};
 for(unsigned i=0;i<1000;++i) {struct iov_iter from={data,sizeof(data),0,false};assert(logger_write_iter(&io,&from)==80&&from.pos==80);}
 return NULL;
}
int main(void) {
 _Static_assert(sizeof(struct logger_entry)==24,"v2 ABI");
 _Static_assert(sizeof(struct user_logger_entry_compat)==20,"v1 ABI");
 unsigned char *storage=malloc(262144+128), data[6000], saved[8192];assert(storage);
 memset(data,0xa7,sizeof(data));
 logbuf.buffer=storage+64;logbuf.size=8192;assert(!pthread_mutex_init(&logbuf.mutex,NULL));
 struct kiocb io={&logbuf};struct iov_iter from={data,0,0,false};
 unsigned before=atomic_load(&allocs);assert(!logger_write_iter(&io,&from)&&atomic_load(&allocs)==before);
 memset(storage,0x5a,262144+128);memcpy(saved,logbuf.buffer,8192);
 from.count=80;fail_alloc=true;assert(logger_write_iter(&io,&from)==-ENOMEM);fail_alloc=false;
 from.fault=true;assert(logger_write_iter(&io,&from)==-EFAULT);assert(!logbuf.w_off&&!memcmp(saved,logbuf.buffer,8192));
 for(unsigned start=0;start<8192;start+=137) {
  memset(storage,0x5a,262144+128);logbuf.w_off=start;
  from=(struct iov_iter){data,sizeof(data),0,false};
  assert(logger_write_iter(&io,&from)==4076&&from.pos==4076);
  struct logger_entry header={0};unsigned char *h=(unsigned char *)&header;
  for(unsigned i=0;i<24;++i)h[i]=logbuf.buffer[(start+i)&8191];
  assert(header.len==4076&&header.hdr_size==24&&header.pid==123&&header.tid==456&&header.euid==1000&&header.sec==100&&header.nsec==200);
  for(unsigned i=0;i<4076;++i)assert(logbuf.buffer[(start+24+i)&8191]==0xa7);
  assert(logbuf.w_off==((start+24+4076)&8191));
  for(unsigned i=0;i<64;++i)assert(storage[i]==0x5a&&storage[64+8192+i]==0x5a);
 }
 logbuf.size=262144;logbuf.w_off=0;memset(storage,0x5a,262144+128);
 pthread_t a,b;assert(!pthread_create(&a,NULL,writer,(void *)'A'));assert(!pthread_create(&b,NULL,writer,(void *)'B'));
 assert(!pthread_join(a,NULL)&&!pthread_join(b,NULL));
 unsigned counts[2]={0};assert(logbuf.w_off==2000*104);
 for(unsigned pos=0;pos<logbuf.w_off;pos+=104) {
  struct logger_entry header;memcpy(&header,logbuf.buffer+pos,24);assert(header.len==80&&header.hdr_size==24);
  unsigned char value=logbuf.buffer[pos+24];assert(value=='A'||value=='B');counts[value=='B']++;
  for(unsigned i=0;i<80;++i)assert(logbuf.buffer[pos+24+i]==value);
 }
 assert(counts[0]==1000&&counts[1]==1000);free(storage);pthread_mutex_destroy(&logbuf.mutex);
 puts("PASS actual logger writes: v1/v2 sizes, empty/alloc/copy faults, atomic truncation, 60 ring offsets, guard bytes and 2000 concurrent entries.");
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-logger-') as temp:
 p=Path(temp);(p/'test.c').write_text(fixture+actual+main)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-pthread','-fsanitize=undefined','-O2','-I',str(tree),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
