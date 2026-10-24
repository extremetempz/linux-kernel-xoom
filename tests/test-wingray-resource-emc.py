#!/usr/bin/env python3
"""The actual EMC registration routine must be inert in resource-only mode."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root/'sources/kernel-donor/drivers/staging/tegra/clk.c').read_text()
enum = re.search(r'enum\s*\{.*?\};', source, re.S).group()
start = source.index('static int register_shared_emc_clks(')
body = source[start:source.index('\n}', start)+2]
prelude = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#define IS_ENABLED(x) (x)
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define pr_err(...) ((void)0)
struct clk {int unused;};struct shared_emc_clk {int unused;};
static struct clk clk,*emc_clk;
static struct shared_emc_clk virtual_emc_clks[64];
static unsigned gets,adds;static int fail;
static struct clk *clk_get_sys(const char *d,const char *id) {
 assert(!d&&id);gets++;return fail?(struct clk *)(intptr_t)-ENOENT:&clk;
}
static void register_shared_emc_clk(struct shared_emc_clk *c,const char *a,const char *b) {
 assert(c&&a&&b);adds++;
}
'''
main = r'''
int main(void) {
 assert(!register_shared_emc_clks());
#if CONFIG_TEGRA_NVMAP_WINGRAY_RESOURCES || CONFIG_TEGRA_GRHOST_WINGRAY_HOST_TEST
 assert(!gets&&!adds);fail=1;assert(!register_shared_emc_clks());assert(!gets&&!adds);
#else
 assert(gets==1&&adds>0);adds=gets=0;fail=1;assert(register_shared_emc_clks()==-ENOENT);assert(gets==1&&!adds);
#endif
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-resource-emc-') as temp:
    path = Path(temp)/'test.c'
    path.write_text(prelude+enum+body+main)
    for enabled, host in [(0, 0), (1, 0), (0, 1)]:
        binary = Path(temp)/('test'+str(enabled)+str(host))
        subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror',
                        '-DCONFIG_TEGRA_NVMAP_WINGRAY_RESOURCES='+str(enabled),
                        '-DCONFIG_TEGRA_GRHOST_WINGRAY_HOST_TEST='+str(host),
                        str(path),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
print('PASS actual EMC registration: resource-only mode makes no clock lookup or registration; ordinary mode and provider errors retained.')
