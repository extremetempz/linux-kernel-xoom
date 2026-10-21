#!/usr/bin/env python3
"""Execute actual GPT selection control flow with controlled header validation.

Header CRC/media reads are stubbed; this tests fallback scope/order, not CRCs.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'sources/kernel-donor/block/partitions/efi.c').read_text();start=s.index('static int find_valid_gpt(');opening=s.index('{',start);end=opening+1;depth=1
while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
actual=s[start:end]
fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint8_t u8;
typedef uint64_t u64;
typedef uint64_t sector_t;
typedef struct { u64 alternate_lba; } gpt_header;
typedef struct { int unused; } gpt_entry;
typedef struct { int unused; } legacy_mbr;
struct inode { int unused; };
struct bdev { struct inode *bd_inode; };
struct parsed_partitions { struct bdev *bdev; };
#define CONFIG_MOTOROLA_XOOM_BIGPART 1
#define GPT_PRIMARY_PARTITION_TABLE_LBA 1
#define GPT_MBR_PROTECTIVE 1
#define GFP_KERNEL 0
#define le64_to_cpu(x) (x)
#define pr_warn(...) ((void)0)
#define pr_info(...) ((void)0)
#define pr_debug(...) ((void)0)
static bool force_gpt,optin;
static u64 xoom_gpt_sector,sectors,valid_lba,calls[8];
static unsigned ncalls;
static gpt_header header;
static gpt_entry entries;
static u64 i_size_read(struct inode *i) { (void)i;return sectors*512; }
static u64 last_lba(struct bdev *b) { (void)b;return sectors-1; }
static void *kzalloc(size_t n,int flags) { (void)flags;return calloc(1,n); }
static void kfree(void *p) { (void)p; }
static int read_lba(struct parsed_partitions *p,u64 lba,u8 *buf,size_t len);
'''.replace('static int read_lba(struct parsed_partitions *p,u64 lba,u8 *buf,size_t len);','''static int read_lba(struct parsed_partitions *p,u64 lba,uint8_t *buf,size_t len) { (void)p;(void)buf;assert(lba==0);return len; }''')
fixture+=r'''
static int is_pmbr_valid(legacy_mbr *m,sector_t n) { free(m);assert(n==sectors);return 0; }
static int is_gpt_valid(struct parsed_partitions *p,u64 lba,gpt_header **g,gpt_entry **e) {
 (void)p;calls[ncalls++]=lba;
 if(lba!=valid_lba)return 0;*g=&header;*e=&entries;return 1;
}
static void compare_gpts(gpt_header *a,gpt_header *b,u64 last) { (void)a;(void)b;assert(last==sectors-1); }
static bool xoom_bigpart_enabled(struct parsed_partitions *p) { (void)p;return optin; }
'''
main=r'''
static void run_case(struct parsed_partitions *state,u64 capacity,u64 location,u64 valid,bool forced,bool scoped,unsigned expected_calls,int expected) {
 sectors=capacity;xoom_gpt_sector=location;valid_lba=valid;force_gpt=forced;optin=scoped;ncalls=0;
 gpt_header *g=NULL;gpt_entry *p=NULL;
 assert(find_valid_gpt(state,&g,&p)==expected);assert(ncalls==expected_calls);
 if(expected)assert(g==&header && p==&entries);else assert(!g && !p);
}
int main(void) {
 struct inode inode;struct bdev b={&inode};struct parsed_partitions state={&b};
 const u64 full=62521344,relocated=62513151;header.alternate_lba=full-1;
 run_case(&state,full,relocated,relocated,true,true,3,1);
 assert(calls[0]==1 && calls[1]==full-1 && calls[2]==relocated);
 run_case(&state,full,relocated,relocated,true,false,2,0);
 run_case(&state,full,relocated,relocated,false,true,0,0);
 run_case(&state,full,full,relocated,true,true,2,0);
 run_case(&state,full,1,relocated,true,true,2,0);
 run_case(&state,full,relocated,full-1,true,true,2,1);
 run_case(&state,relocated+1,relocated,relocated,true,true,2,1);
 run_case(&state,full,relocated,1,true,true,4,1);
 assert(calls[0]==1 && calls[1]==full-1 && calls[2]==full-1 && calls[3]==relocated);
 puts("PASS 8 actual GPT-selection cases: scoped relocated fallback, physical-end preference, reduced/full capacities and invalid gates.");
}
'''
# Make the controlled validator's branch unambiguous under -Werror.
fixture=fixture.replace('if(lba!=valid_lba)return 0;*g=', 'if(lba!=valid_lba)return 0;\n *g=')
with tempfile.TemporaryDirectory(prefix='xoom-gpt-select-') as temp:
 p=Path(temp);(p/'test.c').write_text(fixture+actual+main)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
