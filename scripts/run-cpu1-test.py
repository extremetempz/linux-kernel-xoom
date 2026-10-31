#!/usr/bin/env python3
"""Run one CPU1 offline/online diagnostic; USB stays powered during this test."""
from pathlib import Path
import argparse, array, base64, binascii, datetime, fcntl, getpass, hashlib, json, os, re, secrets, select, termios, time, tty
from diagnostic_protocol import handshake, write_request, ProtocolError
ROOT=Path(__file__).resolve().parents[1]
P=argparse.ArgumentParser(description=__doc__);P.add_argument('--output-dir',type=Path,required=True);P.add_argument('--port',type=Path);P.add_argument('--timeout',type=int,default=30)
A=P.parse_args()
if not 5<=A.timeout<=90:P.error('timeout 5..90')
OUT=A.output_dir.resolve()
if not OUT.is_relative_to((ROOT/'artifacts').resolve()) or OUT.exists():P.error('Use a new private output directory under artifacts/')
ports=[]
for e in Path('/sys/class/tty').glob('ttyACM*'):
 if not re.fullmatch(r'ttyACM[0-9]+',e.name):continue
 cur=(e/'device').resolve()
 for usb in [cur,*cur.parents]:
  try:p=((usb/'idVendor').read_text().strip(),(usb/'idProduct').read_text().strip())
  except OSError:continue
  if p==('0525','a4a7'):ports.append(Path('/dev')/e.name)
  break
if A.port:
 if A.port not in ports:P.error('Selected port is not the expected Xoom diagnostic ACM gadget')
 PORT=A.port
else:
 if len(ports)!=1:P.error('Require exactly one connected Xoom diagnostic ACM gadget')
 PORT=ports[0]
try:fd=os.open(PORT,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
except PermissionError:raise SystemExit(f'Host serial access needed. Run: sudo setfacl -m u:{getpass.getuser()}:rw {PORT}')
nonce=secrets.token_hex(16);status={'state':'started','nonce':nonce,'request':'CPU1TEST','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'arbitrary_shell_commands':False}
try:
 OUT.mkdir(parents=True,exist_ok=False);wire=(OUT/'wire-private.bin').open('xb');tty.setraw(fd,termios.TCSANOW);a=termios.tcgetattr(fd);a[2]|=termios.CLOCAL|termios.CREAD;a[4]=a[5]=termios.B115200;termios.tcsetattr(fd,termios.TCSANOW,a);fcntl.ioctl(fd,termios.TIOCMBIS,array.array('i',[termios.TIOCM_DTR|termios.TIOCM_RTS]));handshake(fd,nonce,record=wire.write)
 print('Diagnostic reporter ready; requesting CPU1 offline/online test.',flush=True);write_request(fd,'CPU1TEST',nonce)
 token=nonce.encode();h=re.compile(rb'(?:^|\n)XOOM_CPU1TEST_V1 '+token+rb' ([0-9]{1,6}) ([0-9a-f]{64})\r?\n');end=re.compile(rb'(?:^|\n)XOOM_CPU1TEST_END_V1 '+token+rb'\r?\n');err=re.compile(rb'(?:^|\n)XOOM_ERROR_V2 '+token+rb' ([A-Z_]+)\r?\n');buf=bytearray();deadline=time.monotonic()+A.timeout;payload=None
 while time.monotonic()<deadline:
  if not select.select([fd],[],[],0.5)[0]:continue
  chunk=os.read(fd,65536)
  if not chunk:raise ProtocolError('Serial disconnected')
  wire.write(chunk);buf.extend(chunk)
  m=err.search(buf)
  if m:raise ProtocolError('device CPU1 error: '+m[1].decode())
  hh=h.search(buf)
  if not hh:continue
  ee=end.search(buf,hh.end())
  if not ee:continue
  payload=base64.b64decode(b''.join(buf[hh.end():ee.start()].split()),validate=True)
  if len(payload)!=int(hh[1]) or hashlib.sha256(payload).hexdigest().encode()!=hh[2]:raise ProtocolError('CPU1 frame size/hash mismatch')
  break
 if payload is None:raise TimeoutError('Timed out waiting for CPU1 result')
 if not payload.startswith(b'XOOM_CPU1_TEST_V1\n') or not payload.endswith(b'XOOM_CPU1_TEST_END\n'):raise ProtocolError('CPU1 payload markers missing')
 (OUT/'cpu1-test.txt').write_bytes(payload);lines=payload.splitlines();ok=all(x in lines for x in (b'CPU1TEST_CPU1_OFFLINE',b'CPU1TEST_PASS',b'CPU1TEST_PROCESS_RC 0'))
 status.update(state='verified' if ok else 'failed',bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),cpu1_hotplug_passed=ok)
 for line in payload.decode('ascii','replace').splitlines():
  if line.startswith('CPU1TEST_'):print(line,flush=True)
 if not ok:raise SystemExit('CPU1 test failed; preserve report and do not retry')
finally:
 try:(OUT/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 except OSError:pass
 os.close(fd)
