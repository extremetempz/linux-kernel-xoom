#!/usr/bin/env python3
"""Exercise actual packed shell gate/server on a PTY with inert fake GPU devices."""
from pathlib import Path
import importlib.util,os,pty,select,subprocess,sys,tempfile,time
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
spec=importlib.util.spec_from_file_location('pack',r/'scripts/prepare-gpu-render-diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
e=m.entries(m.runtime_files(),startup_trace=True,render_probe=True,deferred_probe=True)
with tempfile.TemporaryDirectory() as t:
 t=Path(t);run=t/'run';run.mkdir();dev=t/'dev';dev.mkdir()
 for name in ('nvmap','nvhost-ctrl','nvhost-gr2d','nvhost-gr3d','tegra_sema'):(dev/name).touch()
 (t/'interrupts').write_text('fake interrupts\n')
 (t/'report').write_text('#!/bin/busybox sh\necho XOOM_FAKE_BASELINE\n')
 server=e['bin/diagnostic-server'].data.decode().replace('/run/',str(run)+'/').replace('/bin/diagnostic-report',str(t/'report'))
 (t/'server').write_text(server)
 worker=e['bin/gpu-render-start'].data.decode().replace('/run/',str(run)+'/')
 worker=worker.replace('[ -c "/dev/$node" ]','[ -e "'+str(dev)+'/$node" ]')
 worker=worker.replace('/proc/interrupts',str(t/'interrupts'))
 child_line=next(x for x in worker.splitlines() if x.startswith('/bin/busybox timeout -s KILL 35 '))
 child=t/'child';child.write_text('#!/bin/busybox sh\necho job >> '+str(t/'jobs')+'\necho XOOM_EGL_OFFSCREEN_READBACK_PASS\n')
 worker=worker.replace(child_line,'/bin/busybox sh '+str(child)+' > '+str(run/'gpu-probe-output.txt')+' 2>&1')
 (t/'worker').write_text(worker)
 master,slave=pty.openpty();proc=subprocess.Popen(['/bin/busybox','sh',str(t/'server')],stdin=slave,stdout=slave,stderr=subprocess.PIPE);os.close(slave)
 wp=None
 def send(s):os.write(master,s.encode()+b'\n')
 def until(token,timeout=4):
  data=b'';end=time.monotonic()+timeout
  while token not in data:
   left=end-time.monotonic();assert left>0,(token,data)
   if select.select([master],[],[],left)[0]:data+=os.read(master,65536)
  return data
 nonce='1234567890abcdef1234567890abcdef'
 try:
  send('PING '+nonce);until(('XOOM_READY_V2 '+nonce).encode())
  send('GPU_RUN '+nonce);until(('XOOM_GPU_RELEASE_V1 '+nonce+' NOT_READY').encode());assert not (run/'gpu-probe-release').exists()
  env=dict(os.environ,ANDROID_PROPERTY_WORKSPACE='fake-test-fd')
  wp=subprocess.Popen(['/bin/busybox','sh',str(t/'worker')],env=env,stderr=subprocess.PIPE)
  end=time.monotonic()+3
  while not (run/'gpu-probe-ready').exists():assert time.monotonic()<end;time.sleep(.01)
  assert not (t/'jobs').exists()
  send('PING '+nonce);until(('XOOM_READY_V2 '+nonce).encode());assert not (run/'gpu-probe-release').exists()
  send('REPORT '+nonce);data=until(('XOOM_END_V2 '+nonce).encode());assert b'XOOM_REPORT_V2' in data;assert not (run/'gpu-probe-release').exists() and not (t/'jobs').exists()
  for bad in ('GPU_RUN short','GPU_RUN '+nonce+';touch '+str(t/'injected'),'SHELL '+nonce,'GPU_RUN '+'g'*32):send(bad)
  send('PING '+nonce);until(('XOOM_READY_V2 '+nonce).encode());assert not (run/'gpu-probe-release').exists() and not (t/'injected').exists()
  send('GPU_RUN '+nonce);until(('XOOM_GPU_RELEASE_V1 '+nonce+' ARMED').encode());wp.wait(timeout=4)
  assert wp.returncode==0 and (t/'jobs').read_text()=='job\n'
  assert 'XOOM_GPU_RENDER_PASS' in (run/'gpu-render-result.txt').read_text()
  before=(run/'gpu-probe-release').stat().st_mtime_ns
  send('GPU_RUN '+nonce);until(('XOOM_GPU_RELEASE_V1 '+nonce+' ALREADY').encode())
  assert (run/'gpu-probe-release').stat().st_mtime_ns==before and (t/'jobs').read_text()=='job\n'
  print('PASS actual server/worker PTY: no launch before explicit release, PING/REPORT remain read-only, malformed/injected commands rejected, one bounded child, repeated release idempotent')
 finally:
  proc.terminate();proc.wait(timeout=3)
  if wp is not None and wp.poll() is None:wp.terminate();wp.wait(timeout=3)
  os.close(master)
