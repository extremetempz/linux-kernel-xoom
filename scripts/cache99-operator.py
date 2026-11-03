#!/usr/bin/env python3
"""Reply-checked p9 operator terminal. Repair requires --repair and typed consent."""
from pathlib import Path
import argparse,array,fcntl,json,os,re,secrets,select,sys,termios,time,tty
from diagnostic_protocol import handshake,write_request,receive_report,expected_geometry,storage_result
ROOT=Path(__file__).resolve().parents[1]
class Link:
 def __init__(self,fd,wire):self.fd=fd;self.wire=wire;self.buffer=b''
 def send(self,line):
  data=(line+'\n').encode('ascii');self.wire.write(b'\nHOST> '+data);self.wire.flush();os.fsync(self.wire.fileno())
  deadline=time.monotonic()+5
  while data:
   if time.monotonic()>deadline:raise TimeoutError('serial write timeout')
   if select.select([],[self.fd],[],1)[1]:data=data[os.write(self.fd,data):]
 def read(self,deadline):
  if time.monotonic()>deadline:raise TimeoutError('device response timeout')
  if not select.select([self.fd],[],[],1)[0]:return b''
  try:data=os.read(self.fd,65536)
  except BlockingIOError:return b''
  if not data:raise RuntimeError('serial disconnected')
  self.wire.write(data);self.wire.flush();self.buffer+=data
  if len(self.buffer)>1024*1024:raise RuntimeError('serial transcript exceeds bound')
  print(data.decode(errors='replace'),end='',flush=True)
  return data
 def wait(self,token,timeout):
  deadline=time.monotonic()+timeout
  while token not in self.buffer:
   self.read(deadline)
   if b'CACHE99_PREFLIGHT_FAILED_' in self.buffer:raise RuntimeError('physical preflight failed; no repair sent')
  self.buffer=b''

def preflight(link,nonce):
 print('Checking physical p9 hash and exclusions; this can take a minute.',flush=True)
 link.send('PREFLIGHT_P9 '+nonce)
 link.wait(b'CACHE99_PREFLIGHT_PASSED_P9_RO_ALL_OTHERS_RO',180)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repair',action='store_true')
 p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--port',default='/dev/ttyACM0')
 a=p.parse_args();out=a.output_dir.resolve()
 if not out.is_relative_to(ROOT/'artifacts') or out.exists():p.error('use a new output directory under this checkout artifacts/')
 if a.port!='/dev/ttyACM0':p.error('this reviewed procedure uses fixed /dev/ttyACM0')
 if a.repair and not sys.stdin.isatty():p.error('repair requires an interactive terminal, never piped yes/input')
 # Bind exact observed gadget ancestry before opening it.
 device=Path('/sys/class/tty/ttyACM0/device').resolve()
 usb=next((n for n in (device,*device.parents) if (n/'idVendor').exists()),None)
 if usb is None or ((usb/'idVendor').read_text().strip(),(usb/'idProduct').read_text().strip())!=('0525','a4a7'):
  p.error('not the expected Linux diagnostic gadget')
 out.mkdir(mode=0o700);nonce=secrets.token_hex(16);state={'state':'started','repair_requested':a.repair,'confirmation_sent':False}
 fd=None
 try:
  fd=os.open(a.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
  tty.setraw(fd,termios.TCSANOW);attrs=termios.tcgetattr(fd)
  attrs[2]|=termios.CLOCAL|termios.CREAD;attrs[2]&=~termios.CRTSCTS
  attrs[4]=attrs[5]=termios.B115200;termios.tcsetattr(fd,termios.TCSANOW,attrs)
  fcntl.ioctl(fd,termios.TIOCMBIS,array.array('i',[termios.TIOCM_DTR|termios.TIOCM_RTS]))
  with (out/'wire-private.bin').open('xb') as wire:
   handshake(fd,nonce,record=wire.write);print('USB handshake verified.',flush=True)
   write_request(fd,'REPORT',nonce);report=receive_report(fd,nonce,timeout=60,record=wire.write)
   (out/'report-private.txt').write_bytes(report)
   result=storage_result(report,expected_geometry(ROOT/'artifacts/hardware-private/geometry.txt'),62521344,'offline-cache99')
   print('Fresh RAM tests / all-RO storage report verified.',flush=True)
   state['readonly_report']=result
   link=Link(fd,wire);preflight(link,nonce);state['physical_preflight_passed']=True
   if not a.repair:state['state']='readonly_preflight_passed';return
   print('\nP9 ONLY: type REPAIR_P9 to start the reviewed physical repair. Anything else cancels.\nThis is not a format or host-image restore.',flush=True)
   if input('> ').strip()!='REPAIR_P9':state['state']='cancelled_before_arm';return
   # Recheck on the same live session immediately before arming, after operator delay.
   preflight(link,nonce)
   state['operator_typed_confirmation']=True
   link.send('REPAIR_P9 '+nonce);link.wait(('CACHE99_ARMED '+nonce).encode(),10)
   link.send('REPAIR_P9_CONFIRM '+nonce);state['confirmation_sent']=True
   (out/'status.json').write_text(json.dumps(state,indent=2)+'\n')
   deadline=time.monotonic()+300;answered=False
   prompt=re.compile(rb'Padding at end of inode bitmap is not set\. Fix<y>\?\s*')
   while True:
    link.read(deadline)
    if prompt.search(link.buffer) and not answered:
     answer=input('\nExpected bitmap-padding question. Enter y to correct it, or n to decline: ').strip().lower()
     if answer not in ('y','n'):answer='n'
     link.send(answer);answered=True;link.buffer=b'';deadline=time.monotonic()+180
    elif b'?' in link.buffer and (b'Fix' in link.buffer or b'<y>' in link.buffer or b'<n>' in link.buffer):
     # Never accept an unreviewed repair prompt. Decline it, allowing checker cleanup.
     print('\nUNREVIEWED QUESTION: declining; this attempt cannot be reported successful.',flush=True)
     link.send('n');state['unreviewed_prompt']=True;link.buffer=b''
    if b'CACHE99_REPAIR_COMPLETE_REQUIRES_NEW_READONLY_BACKUP' in link.buffer:
     if b'CACHE99_RELOCKED_RO' not in link.buffer or b'CACHE99_READONLY_RECHECK_EXIT 0' not in link.buffer:
      raise RuntimeError('completion missing checked relock/read-only evidence')
     if state.get('unreviewed_prompt'):raise RuntimeError('unreviewed question occurred; manual review required')
     state['state']='repair_complete_readonly_recheck_passed';print('\nLeave tablet running; share output/status.json.');break
    if any(x in link.buffer for x in (b'CACHE99_REPAIR_FAILED',b'CACHE99_RELOCK_FAILED',b'CACHE99_SYNC_FAILED',b'CACHE99_PREFLIGHT_FAILED_')):
     raise RuntimeError('device reported failure; keep tablet running for review')
 except (Exception,KeyboardInterrupt) as e:
  state.update(state='failed_or_interrupted',error=type(e).__name__+': '+str(e))
  print('\nSTOPPED. Do not restart this tool or reboot blindly. A host interrupt does not prove device repair stopped. Keep tablet connected and share the transcript.',file=sys.stderr)
  raise
 finally:
  (out/'status.json').write_text(json.dumps(state,indent=2)+'\n')
  if fd is not None:os.close(fd)
if __name__=='__main__':main()
