#!/usr/bin/env python3
"""Framing, source-script PTY and read-only report regression checks."""
from pathlib import Path
import base64,hashlib,importlib.util,os,pty,select,socket,subprocess,sys,tempfile,time,unittest
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
from diagnostic_protocol import *
N='0123456789abcdef'*2
M='abcdef0123456789'*2
GEOMETRY={f'mmcblk0p{i}':p for i,p in enumerate([(51200,6144),(57344,4096),(61440,4096),(65536,8192),(73728,4096),(77824,24576),(102400,16384),(118784,2097152),(2215936,1048576),(3264512,59247616)],1)}

def payload(nonce=N,body=b'kernel log\n'):
 return b'XOOM_FRESH_REPORT_V2 '+nonce.encode()+b'\n'+body+b'XOOM_FRESH_REPORT_DONE '+nonce.encode()+b'\n'
def frame(data,nonce=N,size=None,digest=None):
 return (f'XOOM_REPORT_V2 {nonce} {len(data) if size is None else size} {digest or hashlib.sha256(data).hexdigest()}\n'.encode()+base64.encodebytes(data)+f'\nXOOM_END_V2 {nonce}\n'.encode())
def storage_body(parts=GEOMETRY,mount='rootfs / rootfs rw 0 0\n',capacity=70000000):
 return ('XOOM_MOUNTS_BEGIN\n'+mount+'XOOM_MOUNTS_END\n'+f'XOOM_DISK mmcblk0 {capacity} 0\n'+''.join(f'XOOM_PART {n} {s} {z}\n' for n,(s,z) in parts.items())).encode()

class Framing(unittest.TestCase):
 def test_fragments(self):
  data=payload(body=bytes(range(256))*4)
  for chunk in [1,3,7,64,513,65536]:
   parser=FrameDecoder(N);wire=b'XOOM_READY_V2 '+N.encode()+b'\n'+frame(data)
   found=None
   for off in range(0,len(wire),chunk):found=parser.feed(wire[off:off+chunk])
   self.assertEqual(found,data)
 def test_corruption(self):
  data=payload()
  for bad in [frame(data,size=len(data)+1),frame(data,digest='0'*64),frame(payload(M)),frame(data).replace(base64.encodebytes(data),b'@\n'),frame(data,size=MAX_PAYLOAD+1),b'x'*4097,b'x'*(MAX_WIRE+1),f'XOOM_ERROR_V2 {N} REPORT_SIZE\n'.encode()]:
   with self.subTest(bad=bad[:40]),self.assertRaises(ProtocolError):FrameDecoder(N).feed(bad)
 def test_stale_and_incomplete(self):
  self.assertIsNone(FrameDecoder(N).feed(frame(payload(M),M)))
  self.assertIsNone(FrameDecoder(N).feed(frame(payload())[:-10]))
  with self.assertRaises(ProtocolError):FrameDecoder('x')
 def test_timeout_disconnect_and_request_whitelist(self):
  left,right=socket.socketpair()
  try:
   with self.assertRaises(TimeoutError):receive_report(left.fileno(),N,timeout=0.02)
   with self.assertRaises(ProtocolError):write_request(left.fileno(),'EXEC',N)
   write_request(left.fileno(),'PING',N)
   self.assertEqual(right.recv(128),b'PING '+N.encode()+b'\n')
   right.close()
   with self.assertRaisesRegex(ProtocolError,'disconnected'):receive_report(left.fileno(),N,timeout=0.1)
  finally:left.close();right.close()
 def test_geometry(self):
  self.assertEqual(storage_result(storage_body(),GEOMETRY,70000000)['state'],'geometry_matches_reference')
  changed=dict(GEOMETRY);changed['mmcblk0p8']=(118784,524288)
  self.assertEqual(storage_result(storage_body(changed),GEOMETRY)['state'],'geometry_mismatch')
  self.assertEqual(storage_result(storage_body(),GEOMETRY,70000001)['state'],'disk_capacity_mismatch')
  self.assertEqual(storage_result(storage_body({}),GEOMETRY)['state'],'partition_set_mismatch')
  missing=b'XOOM_MOUNTS_BEGIN\nrootfs / rootfs rw 0 0\nXOOM_MOUNTS_END\nXOOM_DISK_MISSING mmcblk0\n'
  self.assertEqual(storage_result(missing,GEOMETRY)['state'],'not_discovered')
  for bad in [storage_body(mount='/dev/mmcblk0p8 /system ext4 ro 0 0\n'),storage_body()+b'XOOM_PART mmcblk0p8 1 2\n',storage_body(capacity=1024)]:
   with self.assertRaises(ProtocolError):storage_result(bad,GEOMETRY)
 def test_overlap(self):
  wrong=dict(GEOMETRY);wrong['mmcblk0p2']=(51201,4096)
  with self.assertRaises(ProtocolError):storage_result(storage_body(wrong),GEOMETRY)
 def test_geometry_reference(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'geometry';path.write_text(''.join(f'/sys/block/mmcblk0/{name}\n{start}\n{size}\n' for name,(start,size) in GEOMETRY.items()))
   self.assertEqual(expected_geometry(path),GEOMETRY)
   path.write_text(path.read_text()+'junk\n')
   with self.assertRaises(ProtocolError):expected_geometry(path)

class ActualScripts(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='xoom-protocol-');self.path=Path(self.temp.name)
  self.busybox='/usr/bin/busybox'
 def tearDown(self):self.temp.cleanup()
 def test_server_pty(self):
  p=self.path;data=storage_body()+bytes(range(256))*32;(p/'fixture').write_bytes(data)
  report=p/'report';report.write_text(f"#!/bin/sh\nprintf 'XOOM_FRESH_REPORT_V2 %s\\n' \"$1\"\n{self.busybox} cat {p/'fixture'}\nprintf 'XOOM_FRESH_REPORT_DONE %s\\n' \"$1\"\n")
  server=(root/'diagnostic/server.sh').read_text().replace('/bin/busybox',self.busybox).replace('/bin/diagnostic-report',str(report)).replace('/run/',str(p)+'/')
  script=p/'server';script.write_text(server)
  master,slave=pty.openpty();os.set_blocking(master,False)
  process=subprocess.Popen([self.busybox,'sh',str(script)],stdin=slave,stdout=slave,stderr=subprocess.PIPE)
  try:
   # Device script must not send a cached report/prompt before a request.
   self.assertFalse(select.select([master],[],[],0.15)[0])
   handshake(master,N,timeout=5)
   for invalid in [b'REPORT short\n',b'REPORT '+b'F'*32+b'\n',b'EXEC touch /tmp/not-allowed\n',b'REPORT $(touch /tmp/not-allowed)\n',b'REPORT '+b'a'*200+b'\n']:
    os.write(master,invalid)
   self.assertFalse(select.select([master],[],[],0.15)[0])
   for nonce in [N,M]:
    write_request(master,'REPORT',nonce)
    result=receive_report(master,nonce,timeout=5)
    self.assertEqual(result,payload(nonce,data))
   (p/'fixture').write_bytes(b'x'*(MAX_PAYLOAD+1))
   write_request(master,'REPORT',N)
   with self.assertRaisesRegex(ProtocolError,'REPORT_SIZE'):receive_report(master,N,timeout=5)
  finally:
   process.terminate();process.wait(timeout=5);os.close(master);os.close(slave)
   errors=process.stderr.read();process.stderr.close()
   self.assertEqual(errors,b'')
 def test_fresh_report_and_bounded_wait(self):
  p=self.path;proc=p/'proc';sysroot=p/'sys';proc.mkdir();sysroot.mkdir()
  for name,data in {'uptime':'35.0 0.0\n','cmdline':'diagnostic\n','partitions':'major minor #blocks name\n','mounts':'rootfs / rootfs rw 0 0\n','interrupts':'0: 1 timer\n'}.items():(proc/name).write_text(data)
  (sysroot/'class/mmc_host').mkdir(parents=True);(sysroot/'bus/mmc/devices').mkdir(parents=True)
  bb=p/'busybox';bb.write_text(f'#!/bin/sh\ncase "$1" in\nsleep) echo tick >> {p/"sleeps"}; exit 0;;\ndmesg) printf "fixture fresh kernel log\\n"; exit 0;;\nesac\nexec {self.busybox} "$@"\n');bb.chmod(0o755)
  report=(root/'diagnostic/report.sh').read_text().replace('/bin/busybox',str(bb)).replace('/proc/',str(proc)+'/').replace('/sys/',str(sysroot)+'/')
  script=p/'report';script.write_text(report)
  # Missing disk yields an explicit bounded negative result, not a match.
  result=subprocess.check_output([self.busybox,'sh',str(script),N]);self.assertIn(b'XOOM_STORAGE_WAIT_SECONDS 20\n',result)
  self.assertEqual((p/'sleeps').read_text().splitlines(),['tick']*20)
  self.assertEqual(storage_result(result,GEOMETRY)['state'],'not_discovered')
  disk=sysroot/'block/mmcblk0';disk.mkdir(parents=True);(disk/'size').write_text('70000000\n');(disk/'ro').write_text('0\n')
  for name,(start,size) in GEOMETRY.items():
   part=disk/name;part.mkdir();(part/'start').write_text(str(start)+'\n');(part/'size').write_text(str(size)+'\n')
  (proc/'uptime').write_text('99.0 0.0\n')
  result=subprocess.check_output([self.busybox,'sh',str(script),M]);self.assertIn(b'XOOM_UPTIME_SNAPSHOT 99.0 0.0\n',result)
  self.assertIn(b'XOOM_STORAGE_WAIT_SECONDS 0\n',result)
  self.assertTrue(result.startswith(b'XOOM_FRESH_REPORT_V2 '+M.encode()+b'\n'))
  self.assertEqual(storage_result(result,GEOMETRY,70000000)['state'],'geometry_matches_reference')

if __name__=='__main__':unittest.main(verbosity=2)
