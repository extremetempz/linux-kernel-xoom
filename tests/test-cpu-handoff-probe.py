#!/usr/bin/env python3
"""Execute the actual bounded CPU-probe logic with syscall fault providers."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'diagnostic/cpu-handoff-probe.c').read_text()
a=s.index('static long call6(');b=s.index('{',a);e=b+1;d=1
while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
s=s[:a]+s[a:b].rstrip()+';'+s[e:]
s=s.replace('__asm__ volatile("dmb ish":::"memory")','__asm__ volatile("":::"memory")').replace('_start','probe_start')
PREFIX=r'''
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <string.h>
enum {OK,BAD_RELEASE,AFFINITY_ERROR,GETCPU_ERROR,WRONG_CPU,CORRUPTION};
static int fault,at_step,steps,gets,rc;static unsigned simulated_cpu;static jmp_buf escaped;
'''
MOCK=r'''
static long call6(long n,long a,long b,long c,long d,long e,long f) {
 assert(!d&&!e&&!f);
 switch(n){
 case 1:rc=a;longjmp(escaped,1);
 case 4:assert(a==1&&b&&c>0&&c<128);return c;
 case 122:assert(a==(long)uts&&!b&&!c);strcpy(uts[2],fault==BAD_RELEASE?"wrong":XOOM_CPU_RELEASE);return 0;
 case 241:
  assert(!a&&b==4&&c==(long)&mask);steps++;
  assert(mask==(1U<<((steps-1)%XOOM_CPU_COUNT)));
  if(fault==AFFINITY_ERROR&&steps==at_step)return -22;
  simulated_cpu=(steps-1)%XOOM_CPU_COUNT;
  if(fault==CORRUPTION&&steps==at_step)page[17]^=1;
  return 0;
 case 345:
  assert(a==(long)&current_cpu&&!b&&!c);gets++;
  if(fault==GETCPU_ERROR&&steps==at_step)return -38;
  current_cpu=simulated_cpu+((fault==WRONG_CPU&&steps==at_step)?1:0);return 0;
 default:assert(!"unexpected syscall");return -38;
 }
}
static void run(int which,int step,int expected){fault=which;at_step=step;steps=gets=0;rc=-999;
 if(!setjmp(escaped))probe_start();assert(rc==expected);
 if(!expected)assert(steps==64&&gets==64);
 if(which==BAD_RELEASE)assert(!steps&&!gets);
}
int main(void){run(OK,0,0);run(BAD_RELEASE,0,1);
 for(int i=1;i<=64;i++){run(AFFINITY_ERROR,i,2);run(GETCPU_ERROR,i,3);run(WRONG_CPU,i,3);run(CORRUPTION,i,4);}
 puts("PASS actual private-memory probe: success and 257 injected failures; bounded CPU affinity/getcpu checks, no unexpected syscalls.");return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-cpu-probe-') as t:
 for count,release in [(1,'4.4.147-wingray-android44-l2'),(1,'4.4.147-wingray-android44-smp'),(2,'4.4.147-wingray-android44-smp2'),(2,'4.4.147-wingray-android44-smptrace')]:
  p=Path(t)/'probe';p.with_suffix('.c').write_text(PREFIX+s+MOCK)
  subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',f'-DXOOM_CPU_COUNT={count}',f'-DXOOM_CPU_RELEASE="{release}"',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  subprocess.run([str(p)],check=True)
