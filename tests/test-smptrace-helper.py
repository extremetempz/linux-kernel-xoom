#!/usr/bin/env python3
"""Exercise the actual C trace helper with substituted MMIO/barrier providers."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='xoom-smp-helper-') as name:
    t=Path(name);(t/'linux').mkdir()
    (t/'linux/io.h').write_text('''#include <stdbool.h>
#include <stdint.h>
typedef uint32_t u32;
#define __iomem
extern unsigned reads,writes; extern uint32_t words[32];
static inline uint32_t readl_relaxed(const void *p) { reads++; return words[((uintptr_t)p-0xfe600000)/4]; }
static inline void writel_relaxed(uint32_t v,void *p) { writes++; words[((uintptr_t)p-0xfe600000)/4]=v; }
#define dsb(x) do {} while(0)
''')
    (t/'test.c').write_text('''#define CONFIG_MOTOROLA_XOOM_SMP_TRACE 1
#define CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE 0x584d0037
#include <soc/tegra/wingray-smptrace.h>
#include <assert.h>
#include <string.h>
unsigned reads,writes; uint32_t words[32]; bool wingray_smptrace_ready;
int main(void) {
 wingray_smptrace_mark(0x10,1); assert(!reads && !writes);
 wingray_smptrace_ready=true;
 for (unsigned off=0;off<256;off++) {
  memset(words,0,sizeof(words));words[0]=WINGRAY_SMPTRACE_MAGIC;words[1]=1;words[2]=CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE;reads=writes=0;
  wingray_smptrace_mark(off,123);
  bool valid=off>=0x10 && off<=0x28 && !(off&3);
  assert(writes==(unsigned)valid);
  if(valid) assert(words[off/4]==123);
  else assert(!reads);
 }
 for(unsigned field=0;field<3;field++) {
  words[0]=WINGRAY_SMPTRACE_MAGIC;words[1]=1;words[2]=CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE;words[field]^=1;writes=0;
  wingray_smptrace_mark(0x18,9);assert(!writes);
 }
 return 0;
}
''')
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-I'+str(t),'-I'+str(root/'sources/kernel-donor/include'),str(t/'test.c'),'-o',str(t/'test')],check=True)
    subprocess.run([str(t/'test')],check=True)
print('PASS: actual C helper rejects unready/invalid headers and all invalid offsets; valid writes bounded to one word. MMIO/barriers substituted, not hardware verified.')
