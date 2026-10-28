#!/usr/bin/env python3
"""Execute donor persistent-RAM/RS code with synthetic reset corruption.

Only allocations, IO copies and spinlocks are mocked. This does not emulate
ARM cache/memory attributes, electrical RAM retention or bootloader writes.
"""
from pathlib import Path
import re
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


core = (K / 'fs/pstore/ram_core.c').read_text()
header = (K / 'include/linux/pstore_ram.h').read_text()
rs_header = re.sub(r'^#include .*$', '', (K / 'include/linux/rslib.h').read_text(), flags=re.M)
rs_source = (K / 'lib/reed_solomon/reed_solomon.c').read_text()
structures = header[header.index('struct persistent_ram_ecc_info {'):header.index('struct persistent_ram_zone *persistent_ram_new')]
buffer = core[core.index('struct persistent_ram_buffer {'):core.index('static inline size_t buffer_size')]
functions = ''.join(function(core, name) for name in (
    'buffer_size', 'buffer_start', 'buffer_start_add', 'buffer_size_add',
    'persistent_ram_encode_rs8', 'persistent_ram_decode_rs8',
    'persistent_ram_update_ecc', 'persistent_ram_update_header_ecc',
    'persistent_ram_ecc_old', 'persistent_ram_init_ecc',
    'persistent_ram_ecc_string', 'persistent_ram_update',
    'persistent_ram_save_old', 'persistent_ram_write',
    'persistent_ram_zap', 'persistent_ram_post_init'))

shim = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
typedef uint32_t u32;
typedef uint64_t phys_addr_t;
typedef int raw_spinlock_t;
typedef struct { int value; } atomic_t;
struct list_head { int dummy; };
#define INIT_LIST_HEAD(x) ((void)(x))
#define PRZ_FLAG_NO_LOCK 1
#define notrace
#define GFP_KERNEL 0
#define kmalloc(n,f) malloc(n)
#define kfree(p) free(p)
#define DIV_ROUND_UP(n,d) (((n)+(d)-1)/(d))
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define pr_devel(...) ((void)0)
#define pr_debug(...) ((void)0)
#define unlikely(x) (x)
#define BUG_ON(x) assert(!(x))
#define min(a,b) ((a)<(b)?(a):(b))
#define raw_spin_lock_irqsave(l,f) ((void)(l),(f)=0)
#define raw_spin_unlock_irqrestore(l,f) ((void)(l),(void)(f))
#define memcpy_toio(d,s,n) memcpy(d,s,n)
#define memcpy_fromio(d,s,n) memcpy(d,s,n)
static int atomic_read(const atomic_t *a) {return a->value;}
static void atomic_set(atomic_t *a,int v) {a->value=v;}
'''
rs = function(rs_source, 'rs_init') + r'''
struct rs_control *init_rs(int symsize,int poly,int fcr,int prim,int roots) {
 return rs_init(symsize,poly,NULL,fcr,prim,roots);
}
static void release_rs(struct rs_control *rs) {
 if(rs){free(rs->alpha_to);free(rs->index_of);free(rs->genpoly);free(rs);}
}
''' + function(rs_source, 'encode_rs8') + function(rs_source, 'decode_rs8')
main = r'''
static void attach(struct persistent_ram_zone *z,void *ram,size_t size,int ecc) {
 memset(z,0,sizeof(*z));z->buffer=ram;z->buffer_size=size-sizeof(*z->buffer);
 struct persistent_ram_ecc_info info={.ecc_size=ecc};
 assert(persistent_ram_post_init(z,0,&info)==0);
 if(ecc)assert(z->ecc_info.block_size==128&&z->ecc_info.ecc_size==16);
}
static void dispose(struct persistent_ram_zone *z) {release_rs(z->rs_decoder);free(z->old_log);}
static const char marker[]="XOOM_PSTORE_BOOT 5a938e4d-83e4-4bdb-a8c5-1370ef46fa72 mount_rc=0\n";
int main(void) {
 const size_t zone=0x80000;
 for(int scenario=0;scenario<8;scenario++) {
  void *ram=calloc(1,zone);assert(ram);struct persistent_ram_zone a,b;
  int ecc=scenario?16:0;attach(&a,ram,zone,ecc);
  assert(!a.old_log_size);assert(a.buffer_size<zone);
  size_t actual=a.buffer_size;
  assert(persistent_ram_write(&a,marker,sizeof(marker)-1)==sizeof(marker)-1);
  if(scenario==0||scenario==2) {
   /* Reproduce the observed ASCII 3 -> s, one bit at bit 6. */
   assert(a.buffer->data[20]=='3');a.buffer->data[20]^=0x40;
  } else if(scenario==3) {
   for(int n=20;n<28;n++)a.buffer->data[n]^=0x40; // eight bad symbols
  } else if(scenario==4) {
   a.buffer->sig^=0x40; // header signature must also recover
  } else if(scenario==5) {
   a.buffer->size.value^=0x100000; // otherwise invalid ring bounds
  } else if(scenario==6) {
   a.par_buffer[0]^=0x40; // parity corruption
  } else if(scenario==7) {
   for(int n=5;n<25;n++)a.buffer->data[n]^=(n+1); // beyond correction budget
  }
  dispose(&a);attach(&b,ram,zone,ecc);
  assert(b.buffer_size==actual&&b.old_log_size==sizeof(marker)-1);
  if(scenario==0)assert(memcmp(b.old_log,marker,sizeof(marker)-1));
  else if(scenario==7)assert(b.bad_blocks>0);
  else {
   assert(!memcmp(b.old_log,marker,sizeof(marker)-1));assert(!b.bad_blocks);
   assert(b.corrected_bytes==(scenario==1?0:scenario==3?8:1));
  }
  char notice[128];persistent_ram_ecc_string(&b,notice,sizeof(notice));
  if(scenario==1)assert(!strcmp(notice,"\nNo errors detected\n"));
  if(scenario==7)assert(strstr(notice,"unrecoverable blocks"));
  dispose(&b);free(ram);
 }
 puts("PASS actual donor RS/ram_core: unprotected control reproduces corruption; clean/one-bit/eight-symbol/header/parity recovery; uncorrectable-block report. No hardware claim.");
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-pstore-ecc-') as directory:
    p = Path(directory)
    (p / 'test.c').write_text(shim + rs_header + rs + structures + buffer + functions + main)
    subprocess.run(['cc', '-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Wno-sign-compare', '-Wno-pointer-sign', '-fsanitize=undefined',
                    '-fno-sanitize-recover=all', '-I', str(K / 'lib/reed_solomon'),
                    str(p / 'test.c'), '-o', str(p / 'test')], check=True)
    subprocess.run([str(p / 'test')], check=True)
