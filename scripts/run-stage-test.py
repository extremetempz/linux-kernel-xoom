#!/usr/bin/env python3
"""Trigger or retrieve one late/noirq or syscore diagnostic; never retries."""
from pathlib import Path
import argparse, array, base64, datetime, fcntl, getpass, hashlib, json, os, re, secrets, select, termios, time, tty
from diagnostic_protocol import handshake, write_request, ProtocolError
ROOT=Path(__file__).resolve().parents[1]
P=argparse.ArgumentParser(description=__doc__);P.add_argument('--output-dir',type=Path,required=True);P.add_argument('--stage',choices=('late','syscore','lp2'),required=True);P.add_argument('--status',action='store_true');P.add_argument('--port',type=Path);P.add_argument('--timeout',type=int,default=25)
A=P.parse_args()
if not 5<=A.timeout<=60:P.error('timeout 5..60')
OUT=A.output_dir.resolve()
if not OUT.is_relative_to((ROOT/'artifacts').resolve()) or OUT.exists():P.error('Use a new private output directory under artifacts/')
ports=[]
for e in Path('/sys/class/tty').glob('ttyACM*'):
 if not re.fullmatch(r'ttyACM[0-9]+',e.name):continue
 cur=(e/'device').resolve()
 for usb in [cur,*cur.parents]:
  try:pair=((usb/'idVendor').read_text().strip(),(usb/'idProduct').read_text().strip())
  except OSError:continue
  if pair==('0525','a4a7'):ports.append(Path('/dev')/e.name)
  break
if A.port:
 if A.port not in ports:P.error('Selected port is not the expected Xoom diagnostic ACM gadget')
 PORT=A.port
else:
 if len(ports)!=1:P.error('Require exactly one connected Xoom diagnostic ACM gadget')
 PORT=ports[0]
try:fd=os.open(PORT,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
except PermissionError:raise SystemExit(f'Host serial access needed. Run: sudo setfacl -m u:{getpass.getuser()}:rw {PORT}')
nonce=secrets.token_hex(16);verb={'late':('LATESTATUS','LATETEST'),'syscore':('SYSSTATUS','SYSCTEST'),'lp2':('LP2STATUS','LP2TEST')}[A.stage][0 if A.status else 1]
status={'state':'started','nonce':nonce,'request':verb,'stage':A.stage,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'arbitrary_shell_commands':False}
try:
 OUT.mkdir(parents=True,exist_ok=False);wire=(OUT/'wire-private.bin').open('xb');tty.setraw(fd,termios.TCSANOW);a=termios.tcgetattr(fd);a[2]|=termios.CLOCAL|termios.CREAD;a[4]=a[5]=termios.B115200;termios.tcsetattr(fd,termios.TCSANOW,a);fcntl.ioctl(fd,termios.TIOCMBIS,array.array('i',[termios.TIOCM_DTR|termios.TIOCM_RTS]));handshake(fd,nonce,record=wire.write)
 print(f'Requesting {verb}.',flush=True);write_request(fd,verb,nonce);token=nonce.encode();h=re.compile(rb'(?:^|\n)XOOM_'+verb.encode()+rb'_V1 '+token+rb' ([0-9]{1,6}) ([0-9a-f]{64})\r?\n');end=re.compile(rb'(?:^|\n)XOOM_'+verb.encode()+rb'_END_V1 '+token+rb'\r?\n');buf=bytearray();deadline=time.monotonic()+A.timeout;payload=None
 while time.monotonic()<deadline:
  if not select.select([fd],[],[],0.5)[0]:continue
  chunk=os.read(fd,65536)
  if not chunk:
   status['usb_disconnected']=True
   raise SystemExit('USB disconnected during stage; reconnect and run --status for the saved result')
  wire.write(chunk);buf.extend(chunk)
  hh=h.search(buf)
  if not hh:continue
  ee=end.search(buf,hh.end())
  if not ee:continue
  payload=base64.b64decode(b''.join(buf[hh.end():ee.start()].split()),validate=True)
  if len(payload)!=int(hh[1]) or hashlib.sha256(payload).hexdigest().encode()!=hh[2]:raise ProtocolError('stage frame size/hash mismatch')
  break
 if payload is None:raise TimeoutError('Timed out waiting for stage result')
 (OUT/(A.stage+'-test.txt')).write_bytes(payload);status.update(state='verified',bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
 print(payload.decode('ascii','replace'),end='')
finally:
 try:(OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 except OSError:pass
 os.close(fd)
