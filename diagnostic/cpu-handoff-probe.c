/* SPDX-License-Identifier: GPL-2.0
 * Fixed private-memory migration check, only for isolated CPU experiments.
 * No device opens, control writes, dynamic allocation, fork or kernel settings.
 */
#ifndef XOOM_CPU_RELEASE
#error Define exact experimental release
#endif
#ifndef XOOM_CPU_COUNT
#error Define expected online CPU count
#endif
_Static_assert(XOOM_CPU_COUNT == 1 || XOOM_CPU_COUNT == 2, "Bounded CPU count");
static long call6(long n,long a,long b,long c,long d,long e,long f)
{
 register long r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c;
 register long r3 __asm__("r3")=d,r4 __asm__("r4")=e,r5 __asm__("r5")=f,r7 __asm__("r7")=n;
 __asm__ volatile("svc 0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");return r0;
}
static char uts[6][65];
static volatile unsigned int page[4096];
static unsigned int current_cpu, mask;
static int equal(const char *a,const char *b){unsigned i=0;while(a[i]&&a[i]==b[i])i++;return a[i]==b[i];}
static void line(const char *s){unsigned n=0;while(s[n])n++;call6(4,1,(long)s,n,0,0,0);}
static void finish(int rc) __attribute__((noreturn));
static void finish(int rc){if(rc)line("XOOM_CPU_HANDOFF_FAILED\n");call6(1,rc,0,0,0,0,0);for(;;){}}
static void barrier(void){__asm__ volatile("dmb ish":::"memory");}
void _start(void) __attribute__((noreturn));
void _start(void)
{
 unsigned round,i,previous=0x584d0040U;
 if(call6(122,(long)uts,0,0,0,0,0)<0||!equal(uts[2],XOOM_CPU_RELEASE))finish(1);
 for(i=0;i<4096;i++)page[i]=i^previous;
 for(round=0;round<64;round++) {
  mask=1U<<(round%XOOM_CPU_COUNT);
  if(call6(241,0,sizeof(mask),(long)&mask,0,0,0)<0)finish(2);
  current_cpu=~0U;
  if(call6(345,(long)&current_cpu,0,0,0,0,0)<0||current_cpu!=round%XOOM_CPU_COUNT)finish(3);
  barrier();
  for(i=0;i<4096;i++)if(page[i]!=(i^previous))finish(4);
  previous=0x584d0040U^round;
  for(i=0;i<4096;i++)page[i]=i^previous;
  barrier();
 }
#if XOOM_CPU_COUNT == 2
 line("XOOM_CPU_HANDOFF_PASSED cpus=2 iterations=64 bytes=16384\n");
#else
 line("XOOM_CPU_HANDOFF_PASSED cpus=1 iterations=64 bytes=16384\n");
#endif
 finish(0);
}
