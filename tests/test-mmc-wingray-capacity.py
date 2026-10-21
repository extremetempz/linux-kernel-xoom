#!/usr/bin/env python3
"""Execute the actual donor-capacity policy with controlled board/host metadata."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'sources/kernel-donor/drivers/mmc/core/mmc.c').read_text();start=s.index('static unsigned int mmc_legacy_user_sectors(');opening=s.index('{',start);end=opening+1;depth=1
while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
actual=s[start:end]
fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
#define MMC_CAP_NONREMOVABLE 1U
#define pr_info(...) ((void)0)
struct device_node { bool bigpart; };
struct device { struct device_node *of_node; };
struct mmc_host { struct device *parent; unsigned int caps; };
struct mmc_card { struct mmc_host *host; };
static bool wingray;
static bool of_machine_is_compatible(const char *name) { assert(!strcmp(name,"motorola,wingray"));return wingray; }
static bool of_property_read_bool(struct device_node *n,const char *name) { assert(!strcmp(name,"motorola,xoom-bigpart"));return n && n->bigpart; }
'''
main=r'''
int main(void) {
 const unsigned int sizes[]={4194304,4194305,62521344,0xffffffffU};
 const u8 multipliers[]={0,1,16,255};unsigned int cases=0;
 for(unsigned machine=0;machine<2;++machine)
 for(unsigned optin=0;optin<2;++optin)
 for(unsigned parentkind=0;parentkind<3;++parentkind)
 for(unsigned nonremovable=0;nonremovable<2;++nonremovable)
 for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j) {
  wingray=machine;struct device_node node={optin};
  struct device parent={parentkind==2?&node:NULL};
  struct mmc_host host={parentkind?&parent:NULL,0x80U|nonremovable};
  struct mmc_card card={&host};
  unsigned raw=sizes[i],expected=raw;
  if(raw>4194304 && nonremovable && !(machine && optin && parentkind==2))expected-=multipliers[j]*512U;
  assert(mmc_legacy_user_sectors(&card,raw,multipliers[j])==expected);
  assert(host.caps==(0x80U|nonremovable));++cases;
 }
 printf("PASS %u actual-source capacity cases: board/controller gates, absent parents, removable media, 2GiB boundary and boot multipliers.\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-mmc-capacity-') as temp:
 p=Path(temp);(p/'test.c').write_text(fixture+actual+main)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
