#!/usr/bin/env python3
"""Exercise the actual constructor's explicit child gate in disposable processes."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'stub.c').write_text('int xoom_egl_probe_main(void){return 23;}\n')
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fPIC','-shared',str(root/'diagnostic/egl-probe/preload-entry.c'),str(p/'stub.c'),'-o',str(p/'probe.so')],check=True)
 for gate,expected in [(None,0),('',0),('0',0),('10',0),('1',23)]:
  env=dict(os.environ);env['LD_PRELOAD']=str(p/'probe.so');env.pop('XOOM_EGL_PROBE_CHILD',None)
  if gate is not None:env['XOOM_EGL_PROBE_CHILD']=gate
  r=subprocess.run(['/bin/true'],env=env,capture_output=True,timeout=3)
  assert r.returncode==expected,(gate,r)
  assert (b'XOOM_EGL_ISOLATED_CHILD_BEGIN' in r.stdout)==(expected==23)
print('PASS 5 isolated EGL constructor gate cases; no graphics hardware accessed')
