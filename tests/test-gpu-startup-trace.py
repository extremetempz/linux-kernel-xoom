#!/usr/bin/env python3
"""Test actual trace bounds and fixed-command writer; no device access."""
from pathlib import Path
import importlib.util,struct,subprocess,tempfile,sys
r=Path(__file__).resolve().parents[1]
s=(r/'sources/kernel-donor/arch/arm/mach-tegra/wingray-gputrace.c').read_text();a=s.index('static ssize_t wingray_trace_publish(');e=s.index('\nstatic const struct file_operations',a)
pa=s.index('static int wingray_trace_panic(');pe=s.index('{',pa)+1;depth=1
while depth:depth+=(s[pe]=='{')-(s[pe]=='}');pe+=1
with tempfile.TemporaryDirectory() as t:
 t=Path(t);(t/'linux').mkdir()
 (t/'linux/io.h').write_text('''#include <stdbool.h>
#include <stdint.h>
typedef uint32_t u32;
#define __iomem
extern unsigned reads,writes;extern u32 words[32];
static inline u32 readl_relaxed(const void*p){reads++;return words[((uintptr_t)p-0xfe600000)/4];}
static inline void writel_relaxed(u32 v,void*p){writes++;words[((uintptr_t)p-0xfe600000)/4]=v;}
#define dsb(x) do {} while(0)
''')
 prefix=r'''
#define CONFIG_MOTOROLA_XOOM_GPU_STARTUP_TRACE 1
#define CONFIG_MOTOROLA_XOOM_SMP_TRACE 1
#define CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE 0x584d0049
#include <soc/tegra/wingray-gputrace.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <sys/types.h>
#include <string.h>
#define __user
#define CAP_SYS_ADMIN 21
#define NOTIFY_DONE 0
struct notifier_block{int unused;};
struct file{int unused;};struct kiocb{int unused;};
struct iov_iter{const char *one,*two;size_t n1,n2,limit;};
static size_t iov_iter_count(struct iov_iter*i){return i->n1+i->n2;}
static size_t copy_from_iter(void*d,size_t n,struct iov_iter*i){size_t done=0;const char*p[2]={i->one,i->two};size_t lens[2]={i->n1,i->n2};for(int j=0;j<2;j++)for(size_t k=0;k<lens[j]&&done<n&&done<i->limit;k++)((char*)d)[done++]=p[j][k];return done;}

unsigned reads,writes;u32 words[32];bool wingray_smptrace_ready;
static int privileged=1,badcopy;
static int capable(int cap){assert(cap==21);return privileged;}
static int copy_from_user(void*d,const void*s,size_t n){if(badcopy)return 1;memcpy(d,s,n);return 0;}
'''
 main=r'''
static void valid(void){memset(words,0,sizeof(words));words[0]=WINGRAY_SMPTRACE_MAGIC;words[1]=1;words[2]=CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE;reads=writes=0;}
int main(void){loff_t pos=0;valid();
 assert(wingray_trace_write(NULL,"1\n",2,&pos)==-ENODEV&&!writes);wingray_smptrace_ready=true;
 for(unsigned off=0;off<256;off++){valid();wingray_gputrace_mark(off,123);assert(writes==(unsigned)(off>=0x10&&off<=0x68&&!(off&3)));}
 for(unsigned h=0;h<3;h++){valid();words[h]^=1;wingray_gputrace_engine(1,53,0);assert(!writes);}
 for(unsigned index=0;index<12;index++){valid();wingray_gputrace_engine(index,53,-EIO);assert(writes==((index==1||index==2||index==10)?3u:0u));}
 valid();wingray_gputrace_runtime(1,0x522,-EIO);
#if CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE == 0x584d0056
 assert(writes==3&&words[WG_GR3D/4]==0x522&&(int)words[WG_GR3D_RET/4]==-EIO);
#else
 assert(!writes);
#endif
 for(int c=0;c<128;c++){valid();char code[2]={c,'\n'};int result=wingray_trace_write(NULL,code,2,&pos);int ok=(c>='1'&&c<='5')||(c>='A'&&c<='C')||(CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE==0x584d0057&&c>='D'&&c<='F');assert(result==(ok?2:-EINVAL));assert(writes==(unsigned)ok);}
#if CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE == 0x584d0057
 for(int c='D';c<='F';c++){valid();char code[2]={c,'\n'};assert(wingray_trace_write(NULL,code,2,&pos)==2);assert(words[WG_USB/4]==(unsigned)(c-'D'+3)&&words[WG_REPORTER/4]==0&&words[WG_USER/4]==0);}
#endif
 valid();privileged=0;assert(wingray_trace_write(NULL,"1\n",2,&pos)==-EPERM&&!writes);privileged=1;
 assert(wingray_trace_write(NULL,"1",1,&pos)==-EINVAL&&!writes);assert(wingray_trace_write(NULL,"1x",2,&pos)==-EINVAL&&!writes);
 badcopy=1;assert(wingray_trace_write(NULL,"1\n",2,&pos)==-EFAULT&&!writes);
 valid();struct iov_iter v={"1","\n",1,1,2};assert(wingray_trace_write_iter(NULL,&v)==2&&words[WG_USER/4]==1&&writes==1);
 valid();v.limit=1;assert(wingray_trace_write_iter(NULL,&v)==-EFAULT&&!writes);v.limit=2;v.n2=0;assert(wingray_trace_write_iter(NULL,&v)==-EINVAL&&!writes);v.n2=2;assert(wingray_trace_write_iter(NULL,&v)==-EINVAL&&!writes);v.n2=1;
 privileged=0;assert(wingray_trace_write_iter(NULL,&v)==-EPERM&&!writes);privileged=1;
 for(int c=0;c<128;c++){valid();char one=c;v=(struct iov_iter){&one,"\n",1,1,2};int ok=(c>='1'&&c<='5')||(c>='A'&&c<='C')||(CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE==0x584d0057&&c>='D'&&c<='F');assert(wingray_trace_write_iter(NULL,&v)==(ok?2:-EINVAL));assert(writes==(unsigned)ok);}
 valid();assert(!wingray_trace_panic(NULL,0,"VFS: Unable to mount root fs"));assert(words[WG_PANIC/4]==1);
#if CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE == 0x584d0050 || CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE == 0x584d0051
 assert(!memcmp((char*)words+0x6c,"VFS: Unable to mount ",20));
 valid();assert(!wingray_trace_panic(NULL,0,"short"));assert(!memcmp((char*)words+0x6c,"short\0",6));for(int i=0x6c+5;i<128;i++)assert(!((char*)words)[i]);
 valid();assert(!wingray_trace_panic(NULL,0,NULL));for(int i=0x6c;i<128;i++)assert(!((char*)words)[i]);
#else
 for(int i=0x6c;i<128;i++)assert(!((char*)words)[i]);
#endif
 puts("PASS actual retained helper bounds, stale header rejection, engine slots and privileged fixed-command writer (UBSan)");}
'''
 c=t/'test.c';c.write_text(prefix+s[a:e]+s[pa:pe]+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test')],check=True);subprocess.run([str(t/'test')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0050').replace('off<=0x68','off<=0x7c'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test50')],check=True);subprocess.run([str(t/'test50')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0051').replace('off<=0x68','off<=0x7c'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test51')],check=True);subprocess.run([str(t/'test51')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0052').replace('off<=0x68','off<=0x7c').replace('== 0x584d0051','== 0x584d0052'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test52')],check=True);subprocess.run([str(t/'test52')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0053').replace('off<=0x68','off<=0x7c').replace('== 0x584d0051','== 0x584d0053'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test53')],check=True);subprocess.run([str(t/'test53')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0054').replace('off<=0x68','off<=0x7c').replace('== 0x584d0051','== 0x584d0054'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test54')],check=True);subprocess.run([str(t/'test54')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0055').replace('off<=0x68','off<=0x7c').replace('== 0x584d0051','== 0x584d0055'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test55')],check=True);subprocess.run([str(t/'test55')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0056').replace('off<=0x68','off<=0x7c').replace('== 0x584d0051','== 0x584d0056'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test56')],check=True);subprocess.run([str(t/'test56')],check=True)
 c.write_text((prefix+s[a:e]+s[pa:pe]+main).replace('0x584d0049','0x584d0057').replace('off<=0x68','off<=0x7c').replace('== 0x584d0051','== 0x584d0057').replace('== 0x584d0056','== 0x584d0057'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-I'+str(t),'-I'+str(r/'sources/kernel-donor/include'),str(c),'-o',str(t/'test57')],check=True);subprocess.run([str(t/'test57')],check=True)
spec=importlib.util.spec_from_file_location('decode',r/'scripts/decode-gpu-startup-trace.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
w=[0]*32;w[:3]=[0x58534d50,1,m.COOKIE];w[0x2c//4]=0xc0123450;w[0x34//4]=2;w[0x30//4]=0xffffffed
assert m.decode(struct.pack('<32I',*w),'c0123450 t example_init\n')['initcall_result']==-19
for at in [0,1,2,3,27,31]:
 changed=w[:];changed[at]^=1
 try:m.decode(struct.pack('<32I',*changed),'c0123450 t example_init\n')
 except AssertionError:pass
 else:raise AssertionError('Accepted corrupt/stale record')
try:m.decode(struct.pack('<32I',*w),'c0123454 t wrong_build\n')
except AssertionError:pass
else:raise AssertionError('Accepted wrong symbol map')
print('PASS decoder rejects stale/corrupt records and mismatched symbol maps')

msg=b'VFS: Unable to mount '[:20]
w50=bytearray(struct.pack('<32I',*w));struct.pack_into('<I',w50,8,0x584d0050);w50[0x6c:0x80]=msg
assert m.decode(bytes(w50),'c0123450 t example_init\n',cookie=0x584d0050)['panic_prefix']==msg.decode()
print('PASS cookie-50 bounded panic prefix and separate cookie handling')

w52=bytearray(w50);struct.pack_into('<I',w52,8,0x584d0052);struct.pack_into('<I',w52,0x68,1);w52[0x6c:0x80]=b'RD 1234abcd 00320725'
d=m.decode(bytes(w52),'c0123450 t example_init\n',cookie=0x584d0052)
assert d['initrd_fnv1a32']=='1234abcd' and d['initrd_size']==0x320725
print('PASS cookie-52 complete retained input fingerprint/size decoding')

struct.pack_into('<I',w52,8,0x584d0053)
d=m.decode(bytes(w52),'c0123450 t example_init\n',cookie=0x584d0053)
assert d['initrd_fnv1a32']=='1234abcd' and d['initrd_size']==0x320725
print('PASS cookie-53 metadata decoding and fresh-cookie handling')

w56=bytearray(w52);struct.pack_into('<I',w56,8,0x584d0056);struct.pack_into('<I',w56,0x48,0x522)
d=m.decode(bytes(w56),'c0123450 t example_init\n',cookie=0x584d0056)
assert d['gr3d_runtime']=={'operation':'ioctl entry','number':0x22}
assert 'bounded userspace rendering probe is enabled' in d['limits']
print('PASS cookie-56 runtime operation decoding')

w57=bytearray(w56);struct.pack_into('<I',w57,8,0x584d0057)
for stage,label in [(3,'before readiness printf'),(4,'readiness printf returned success'),(5,'readiness printf returned failure')]:
 struct.pack_into('<I',w57,0x60,stage)
 assert m.decode(bytes(w57),'c0123450 t example_init\n',cookie=0x584d0057)['usb_reply_checkpoint']==label
print('PASS cookie57 independent reply checkpoint decoding')
