#!/usr/bin/env python3
"""Compile actual donor voltage constants/table; no regulator operations."""
from pathlib import Path
import re,resource,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];TREE=ROOT/'sources/kernel-donor';PATH='drivers/staging/tegra/tegra20-dvfs.c'
with tempfile.TemporaryDirectory(prefix='xoom-dvfs-units-') as t:
 def run(s,n):
  defines='\n'.join(re.findall(r'^#define (?:_100uV|CPU_MAX_VDD|CORE_MAX_VDD)\b.*$',s,re.M))
  table=re.search(r'static const int core_millivolts\[7\] = .*?;',s,re.S).group()
  p=Path(t)/n;p.with_suffix('.c').write_text('#include <assert.h>\n'+defines+'\n'+table+'\nint main(void){assert(CORE_MAX_VDD-CPU_MAX_VDD==100);assert(core_millivolts[6]==1475);for(int i=0;i<7;i++)assert(core_millivolts[i]>=950&&core_millivolts[i]<=1475);return 0;}')
  subprocess.run(['cc','-std=c11','-Wall','-Werror',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  return subprocess.run([str(p)],capture_output=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
 current=run((TREE/PATH).read_text(),'current');assert current.returncode==0,current.stderr
 old=subprocess.check_output(['git','-C',str(TREE),'show','77d1c0ed:'+PATH],text=True)
 before=run(old,'before');assert before.returncode!=0 and b'Assertion' in before.stderr,before.stderr
print('PASS actual donor table keeps millivolt units (1475, not 101375). This is not a validated Motorola voltage limit; driver stays disabled.')
