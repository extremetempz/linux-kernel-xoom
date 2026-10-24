#!/usr/bin/env python3
"""Exercise packed readiness reply over a PTY and an actual failed write."""
from pathlib import Path
import gzip, importlib.util, os, pty, subprocess, sys, tempfile, time
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'scripts'))
spec=importlib.util.spec_from_file_location('pack',r/'scripts/prepare-gpu-render-diagnostic.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from diagnostic_protocol import handshake
entries=m.entries(m.runtime_files(),startup_trace=True,render_probe=True,deferred_probe=True,usb_reply_trace=True)
source=entries['bin/diagnostic-server'].data.decode()
old=m.entries(m.runtime_files(),startup_trace=True,render_probe=True,deferred_probe=True)['bin/diagnostic-server'].data
assert b'printf "D\\n"' not in old # build 56 runtime remains unchanged
assert m.pack_newc(m.entries(m.runtime_files(),startup_trace=True,render_probe=True,deferred_probe=True)) == gzip.decompress((r/'artifacts/gpu-render56-kernel/builtin-initramfs.cpio.gz').read_bytes())
nonce='1234567890abcdef1234567890abcdef'
for failure in (False,True):
 with tempfile.TemporaryDirectory() as tmp:
  t=Path(tmp);trace=t/'trace';trace.touch()
  server=source.replace('/dev/xoom-startup-trace',str(trace)).replace('[ ! -c ', '[ ! -e ').replace(' > '+str(trace),' >> '+str(trace)).replace('/run/',str(t)+'/')
  if failure:
   needle='/bin/busybox printf \'XOOM_READY_V2 %s\\n\' "$nonce"'
   assert server.count(needle)==1
   server=server.replace(needle,needle+' >&-')
  path=t/'server';path.write_text(server)
  master,slave=pty.openpty()
  p=subprocess.Popen(['/bin/busybox','sh',str(path)],stdin=slave,stdout=slave,stderr=subprocess.PIPE)
  os.close(slave)
  try:
   if not failure:
    handshake(master,nonce,timeout=3)
    want='C\nD\nE\n'
   else:
    os.write(master,('PING '+nonce+'\n').encode());want='C\nD\nF\n'
   end=time.monotonic()+3
   while want not in trace.read_text():
    assert time.monotonic()<end,trace.read_text();time.sleep(.01)
   assert not (t/'gpu-probe-release').exists()
  finally:
   p.terminate();p.wait(timeout=3);os.close(master)
print('PASS packed server + real host handshake; successful write E, failed write F, GPU remains gated, build56 path unchanged')
