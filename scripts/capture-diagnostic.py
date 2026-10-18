#!/usr/bin/env python3
"""Capture only the Linux g_serial ACM gadget, keeping raw logs private."""
from pathlib import Path
import argparse, array, fcntl, os, select, termios, time, tty
p=argparse.ArgumentParser();p.add_argument('--timeout',type=int,default=90);args=p.parse_args()
root=Path(__file__).resolve().parents[1]
log=root/'artifacts/hardware-private/diagnostic-usb-serial.txt'
end=time.monotonic()+args.timeout
port=None
while time.monotonic()<end:
 for item in Path('/sys/class/tty').glob('ttyACM*'):
  for parent in (item.resolve(),*item.resolve().parents):
   try:
    vendor=(parent/'idVendor').read_text().strip()
    product=(parent/'idProduct').read_text().strip()
   except OSError:continue
   if (vendor,product)==('0525','a4a7'):
    port=Path('/dev')/item.name
    break
  if port:break
 if port:break
 time.sleep(0.5)
if not port:raise SystemExit('No Xoom diagnostic USB ACM gadget detected within timeout.')
fd=os.open(port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
try:
 tty.setraw(fd)
 fcntl.ioctl(fd,termios.TIOCMBIS,array.array('i',[termios.TIOCM_DTR|termios.TIOCM_RTS]))
 time.sleep(0.5)
 os.write(fd,b'\n/bin/busybox cat /run/boot-report.txt\n')
 with log.open('ab') as output:
  while time.monotonic()<end:
   if select.select([fd],[],[],1)[0]:
    try:data=os.read(fd,65536)
    except OSError:break
    if not data:break
    output.write(data);output.flush()
 print('Diagnostic USB capture saved locally:',log)
finally:os.close(fd)
