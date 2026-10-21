#!/usr/bin/env python3
"""Compile actual legacy setup dispatcher and GPT option handlers.

Controlled setup arrays cover both handler orders; media/CRC is not simulated.
The pre-fix control differs only by removing the exact-token guard.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]

def function(source, start):
    offset = source.index(start)
    opening = source.index('{', offset)
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[offset:end]

source = (root/'sources/kernel-donor/block/partitions/efi.c').read_text()
force = function(source, 'static int __init\nforce_gpt_fn(')
sector = function(source, 'static int __init xoom_gpt_sector_setup(')
dispatch = function((root/'sources/kernel-donor/init/main.c').read_text(),
                    'static int __init obsolete_checksetup(')
guard = '\tif (*str)\n\t\treturn 0;\n'
assert guard in force, 'GPT handler must reject nonempty suffixes before setting force_gpt'
legacy = force.replace(guard, '', 1).replace('force_gpt_fn(', 'legacy_force_gpt_fn(', 1)
fixture = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define __init
#define pr_warn(...) ((void)0)
typedef uint64_t u64;
static int force_gpt;
static u64 xoom_gpt_sector;
struct obs_kernel_param { const char *str; int (*setup_func)(char *); int early; };
static struct obs_kernel_param entries[2];
#define __setup_start entries
#define __setup_end (entries+2)
static int parameqn(const char *a,const char *b,size_t n) { return !strncmp(a,b,n); }
static int kstrtoull(char *arg,int base,u64 *out) {
 char *end;errno=0;unsigned long long value=strtoull(arg,&end,base);
 if(errno || end==arg || *end || *arg=='-')return -1;
 *out=value;return 0;
}
'''
main = r'''
static void set_order(int reverse,int old) {
 struct obs_kernel_param broad={"gpt",old?legacy_force_gpt_fn:force_gpt_fn,0};
 struct obs_kernel_param narrow={"gpt_sector=",xoom_gpt_sector_setup,0};
 entries[reverse]=broad;entries[!reverse]=narrow;
 force_gpt=0;xoom_gpt_sector=0;
}
static int option(const char *text) {
 char line[128];assert(strlen(text)<sizeof(line));strcpy(line,text);
 return obsolete_checksetup(line);
}
int main(void) {
 set_order(0,1);assert(option("gpt_sector=0x03b9dfff"));
 assert(force_gpt==1 && xoom_gpt_sector==0);
 set_order(1,1);assert(option("gpt_sector=0x03b9dfff"));
 assert(force_gpt==0 && xoom_gpt_sector==62513151);
 for(int reverse=0;reverse<2;++reverse) {
  set_order(reverse,0);assert(option("gpt"));assert(force_gpt==1);
  assert(option("gpt_sector=0x03b9dfff"));assert(xoom_gpt_sector==62513151);
  set_order(reverse,0);assert(option("gpt_sector=62513151"));
  assert(force_gpt==0 && xoom_gpt_sector==62513151);
  assert(option("gpt"));assert(force_gpt==1 && xoom_gpt_sector==62513151);
  const char *bad[]={"gptfoo","gpt=1","gpt_sector_typo=0x03b9dfff"};
  for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);++i) {
   set_order(reverse,0);assert(!option(bad[i]));
   assert(force_gpt==0 && xoom_gpt_sector==0);
  }
  const char *invalid[]={"gpt_sector=","gpt_sector=xyz","gpt_sector=-1"};
  for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) {
   set_order(reverse,0);assert(option(invalid[i]));
   assert(force_gpt==0 && xoom_gpt_sector==0);
  }
 }
 puts("PASS: actual setup dispatcher/handlers reproduce prefix loss; fixed parsing is order-independent, with suffix/invalid-value controls.");
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-gpt-options-') as temp:
    p = Path(temp)
    (p/'test.c').write_text(fixture + force + '\n' + legacy + '\n' + sector + '\n' + dispatch + main)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
                    '-fsanitize=undefined','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
