#!/usr/bin/env python3
"""Release one preconfigured bounded RAM-only GPU child after verified USB baseline."""
from pathlib import Path
import argparse,array,datetime,fcntl,hashlib,json,os,re,secrets,select,termios,time,tty
from diagnostic_protocol import handshake,_read
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--attempt-dir',type=Path,required=True)
p.add_argument('--baseline-dir',type=Path,required=True)
p.add_argument('--output-dir',type=Path,required=True)
p.add_argument('--port',type=Path,default=Path('/dev/ttyACM0'))
a=p.parse_args()
for directory in (a.attempt_dir,a.baseline_dir):
 assert directory.resolve().is_relative_to(ROOT/'artifacts') and directory.is_dir()
out=a.output_dir.resolve();assert out.is_relative_to(ROOT/'artifacts') and not out.exists()
state=json.loads((a.attempt_dir/'test-state-private.json').read_text())
manifest=json.loads((ROOT/'artifacts/gpu-render56-ready/manifest.json').read_text())
assert state['original_restoration_pending'] and state['rendering_enabled'] and state['stage']=='candidate-observation'
assert state['candidate_sha256']==manifest['sha256'] and manifest['deferred_probe'] and manifest['trace_cookie']=='0x584d0056'
status=json.loads((a.baseline_dir/'capture-status.json').read_text());payload=(a.baseline_dir/'report-private.txt').read_bytes()
assert status['state']=='verified' and status['report_integrity']=='verified'
assert hashlib.sha256(payload).hexdigest()==status['sha256']
for token in (b'XOOM_GPU_RENDER_WAIT_USB_GATE',b'XOOM_GPU_RENDER_DEVICES_READY',b'XOOM_GPU_PROPERTY_WORKSPACE_PRESENT'):
 assert token in payload,token
assert b'XOOM_GPU_RENDER_EXIT ' not in payload and b'XOOM_GPU_RENDER_GATE_TIMEOUT' not in payload
assert b'XOOM_GPU_RENDER_PASS' not in payload
current=(Path('/sys/class/tty')/a.port.name/'device').resolve()
assert re.fullmatch(r'ttyACM[0-9]+',a.port.name) and a.port==Path('/dev')/a.port.name
for node in (current,*current.parents):
 if (node/'idVendor').is_file():
  assert (node/'idVendor').read_text().strip()=='0525' and (node/'idProduct').read_text().strip()=='a4a7';break
else:raise AssertionError('Expected diagnostic gadget not found')
fd=os.open(a.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK);nonce=secrets.token_hex(16)
record={'state':'started','nonce':nonce,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requests':['PING','GPU_RUN'],'arbitrary_shell_commands':False,'release_may_have_occurred':False,'baseline_sha256':status['sha256']}
out.mkdir()
try:
 tty.setraw(fd,termios.TCSANOW);attrs=termios.tcgetattr(fd);attrs[2]|=termios.CLOCAL|termios.CREAD;attrs[4]=attrs[5]=termios.B115200;termios.tcsetattr(fd,termios.TCSANOW,attrs)
 fcntl.ioctl(fd,termios.TIOCMBIS,array.array('i',[termios.TIOCM_DTR|termios.TIOCM_RTS]))
 with (out/'wire-private.bin').open('xb') as wire:
  handshake(fd,nonce,record=wire.write)
  request=('GPU_RUN '+nonce+'\n').encode();deadline=time.monotonic()+2
  record['release_may_have_occurred']=True
  (out/'release-status.json').write_text(json.dumps(record,indent=2)+'\n')
  while request:
   remaining=deadline-time.monotonic();assert remaining>0 and select.select([],[fd],[],remaining)[1]
   try:n=os.write(fd,request)
   except BlockingIOError:continue
   assert n>0;request=request[n:]
  response=bytearray();deadline=time.monotonic()+10
  pattern=re.compile(rb'(?:^|\n)XOOM_GPU_RELEASE_V1 '+nonce.encode()+rb' (ARMED|ALREADY|NOT_READY)\r?\n')
  while True:
   response.extend(_read(fd,deadline,wire.write));assert len(response)<=4096
   match=pattern.search(response)
   if match:break
  record['response']=match[1].decode();assert match[1]==b'ARMED','Probe was not newly armed; do not retry automatically'
  record['state']='released'
  print('One bounded GPU child released after verified baseline. No arbitrary shell command sent.')
finally:
 os.close(fd);(out/'release-status.json').write_text(json.dumps(record,indent=2)+'\n')
