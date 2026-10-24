#!/usr/bin/env python3
"""Run the actual nvhost write loop with replacing-job providers; no hardware."""
from pathlib import Path
import resource, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
TREE=ROOT/'sources/kernel-donor'
PATH='drivers/staging/tegra/video/host/bus_client.c'
def function(s,name):
 a=s.index(name+'(');start=s.rfind('\nstatic ',0,a)+1;b=s.index('{',a);end=b+1;depth=1
 while depth: depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]
PREFIX=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#define __user
#define wingray_gputrace_runtime(i,s,r) do {} while(0)
typedef uint32_t u32;
#ifdef CONFIG_TEGRA_GRHOST_WINGRAY_LEGACY_SUBMIT
static int of_machine_is_compatible(const char *s) {assert(!strcmp(s,"motorola,wingray"));return TEST_BOARD_WINGRAY;}
#endif
#define NVHOST_SUBMIT_VERSION_V0 0
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
struct nvhost_submit_hdr {uint32_t syncpt_id,syncpt_incrs,num_cmdbufs,num_relocs;};
struct nvhost_submit_hdr_ext {uint32_t syncpt_id,syncpt_incrs,num_cmdbufs,num_relocs,submit_version,num_waitchks,waitchk_mask,pad[5];};
struct nvhost_cmdbuf {uint32_t mem,offset,words;};
struct nvhost_reloc {uint32_t cmdbuf_mem,cmdbuf_offset,target,target_offset;};
struct nvhost_reloc_shift {uint32_t shift;};
struct nvhost_waitchk {uint32_t mem,offset,syncpt_id,thresh;};
struct pin {struct nvhost_reloc reloc;uint32_t reloc_shift;};
struct nvhost_job {int num_pins,num_waitchk;struct pin pinarray[4];struct nvhost_waitchk waitchk[4];};
struct device {int dev;const char *name;};
struct channel {struct device *dev;};
struct nvhost_channel_userctx {struct channel *ch;struct nvhost_job *job;struct nvhost_submit_hdr_ext hdr;int num_relocshifts;};
struct file {struct nvhost_channel_userctx *private_data;};
static struct nvhost_job jobs[4];static int allocated,gathers,resets,copy_fail;
static struct nvhost_job *live;
static int copy_from_user(void *dst,const void *src,size_t n) {
 if(copy_fail)return 1;
 /* No transfer may target a replaced job's pin/wait arrays. */
 uintptr_t d=(uintptr_t)dst;
 for(int i=0;i<allocated;i++)if(d>=(uintptr_t)&jobs[i]&&d<(uintptr_t)(&jobs[i]+1))assert(&jobs[i]==live);
 memcpy(dst,src,n);return 0;
}
static int set_submit(struct nvhost_channel_userctx *p) {
 assert(p->hdr.num_cmdbufs&&allocated<4);live=&jobs[allocated++];p->job=live;return 0;
}
static void nvhost_job_add_gather(struct nvhost_job *j,uint32_t mem,uint32_t words,uint32_t off) {
 assert(j==live&&mem==17&&words==3&&off==4);++gathers;
}
static void reset_submit(struct nvhost_channel_userctx *p){++resets;p->job=NULL;memset(&p->hdr,0,sizeof(p->hdr));}
#define dev_err(...) ((void)0)
#define trace_nvhost_channel_write_submit(...) ((void)chname)
#define trace_nvhost_channel_write_cmdbuf(...) ((void)chname)
#define trace_nvhost_channel_write_waitchks(...) ((void)chname)
'''
MAIN=r'''
int main(void) {
 struct device d={0,"gr3d"};struct channel c={&d};
 struct nvhost_channel_userctx p={.ch=&c,.job=&jobs[0]};struct file f={&p};loff_t off=0;
 allocated=1;live=&jobs[0];
 #ifdef TEST_WINGRAY24
 struct {struct nvhost_submit_hdr_wingray h;struct nvhost_cmdbuf b;struct nvhost_reloc r;struct nvhost_waitchk w;} stream={
  {1,1,1,1,1,8},{17,4,3},{17,4,18,8},{18,12,3,7}};
#else
 struct {struct nvhost_submit_hdr h;struct nvhost_cmdbuf b;struct nvhost_reloc r;} stream={
  {1,1,1,1},{17,4,3},{17,4,18,8}};
#endif
 assert(nvhost_channelwrite(&f,(void*)&stream.h,sizeof(stream.h)-1,&off)==0);
 assert(p.job==live&&!gathers);

 assert(nvhost_channelwrite(&f,(void*)&stream,sizeof(stream),&off)==sizeof(stream));
 assert(gathers==1&&p.job==&jobs[1]&&p.job->num_pins==1);
 assert(p.job->pinarray[0].reloc.target==18&&!resets);
 assert(nvhost_channelwrite(&f,(void*)&stream,sizeof(stream),&off)==sizeof(stream));
 assert(gathers==2&&p.job==&jobs[2]&&p.job->num_pins==1);
 /* Header and body in different writes must retain the replacement too. */
 assert(nvhost_channelwrite(&f,(void*)&stream.h,sizeof(stream.h),&off)==sizeof(stream.h));
 assert(p.job==&jobs[3]);
 assert(nvhost_channelwrite(&f,(void*)&stream.b,sizeof(stream)-sizeof(stream.h),&off)==sizeof(stream)-sizeof(stream.h));
 assert(gathers==3&&p.job->num_pins==1&&!resets);
#ifdef TEST_WINGRAY24
 assert(p.job->num_waitchk==1&&p.job->waitchk[0].thresh==7&&p.hdr.waitchk_mask==8);
#endif
 copy_fail=1;
 assert(nvhost_channelwrite(&f,(void*)&stream.h,sizeof(stream.h),&off)==-EFAULT&&resets==1);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-nvhost-job-') as t:
 def run(source,name,flags=()):
  p=Path(t)/name;p.with_suffix('.c').write_text(PREFIX+source[source.index('struct nvhost_submit_hdr_wingray {'):source.index('static ssize_t nvhost_channelwrite(')] +function(source,'nvhost_channelwrite')+MAIN if 'struct nvhost_submit_hdr_wingray {' in source else PREFIX+function(source,'nvhost_channelwrite')+MAIN)
  subprocess.run(['cc','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined',*flags,str(p.with_suffix('.c')),'-o',str(p)],check=True)
  return subprocess.run([str(p)],capture_output=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
 current=run((TREE/PATH).read_text(),'current');assert current.returncode==0,current.stderr
 for name, flags in [('wingray24',['-DCONFIG_TEGRA_GRHOST_WINGRAY_LEGACY_SUBMIT=1','-DTEST_BOARD_WINGRAY=1','-DTEST_WINGRAY24=1']),('other16',['-DCONFIG_TEGRA_GRHOST_WINGRAY_LEGACY_SUBMIT=1','-DTEST_BOARD_WINGRAY=0'])]:
  result=run((TREE/PATH).read_text(),name,flags);assert result.returncode==0,(name,result.stderr)
 old=subprocess.check_output(['git','-C',str(TREE),'show','77d1c0ed:'+PATH],text=True)
 before=run(old,'before');assert before.returncode!=0 and b'Assertion' in before.stderr,before.stderr
print('PASS actual nvhost write loop follows replaced jobs for combined/split writes; old code fails. Explicit Wingray24 and donor/other-board16 streams, truncated headers and wait checks pass. No graphics hardware exercised.')
