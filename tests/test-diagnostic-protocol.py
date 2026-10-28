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

def android_body(system=True,overlays=True,execute=True,fuse=False,extras=()):
 # (source, target, filesystem, mount options, major:minor, fs root, super options)
 mounts=[('rootfs','/','rootfs','ro','0:1','/','ro'),
         ('tmpfs','/run','tmpfs','rw,nosuid,nodev','0:5','/','rw'),
         ('proc','/proc','proc','rw','0:3','/','rw'),
         ('tmpfs','/data','tmpfs','rw,nosuid,nodev','0:6','/','rw'),
         ('tmpfs','/cache','tmpfs','rw,nosuid,nodev','0:7','/','rw')]
 if system:
  mounts.append(('/dev/mmcblk0p8','/system','ext4','ro,nosuid,nodev,norecovery','179:8','/','ro,norecovery'))
 if overlays:
  mounts.extend([('tmpfs','/system/lib/hw','tmpfs','ro,nosuid,nodev','0:5','/xoom-hw','rw'),
                 ('tmpfs','/system/lib/egl','tmpfs','ro,nosuid,nodev','0:5','/xoom-egl','rw')])
 if fuse:
  mounts.extend([('/dev/fuse','/mnt/shell/emulated','fuse','rw,nosuid,nodev','0:8','/','rw'),
                 ('/dev/fuse','/storage/emulated/0','fuse','rw,nosuid,nodev','0:8','/0','rw')])
 mounts.extend(extras)
 lines=''.join(f'{s} {t} {f} {o} 0 0\n' for s,t,f,o,dev,rt,superopts in mounts)
 body=storage_body(mount=lines,capacity=62521344).replace(b'62521344 0\n',b'62521344 1\n')
 policy=('XOOM_ANDROID44_POLICY_BEGIN_V1\nXOOM_ANDROID44_RELEASE 4.4.147-wingray-android44\n'
         'XOOM_ANDROID44_BOARD motorola,wingray\n')
 policy+=''.join(f'XOOM_ANDROID44_BLOCK_RO {n} 1\n' for n in ['mmcblk0',*[f'mmcblk0p{i}' for i in range(1,11)]])
 policy+='XOOM_ANDROID44_MOUNTINFO_BEGIN\n'
 policy+=''.join(f'{i} 1 {dev} {rt} {t} {o} - {f} {s} {sup}\n' for i,(s,t,f,o,dev,rt,sup) in enumerate(mounts,10))
 policy+=('XOOM_ANDROID44_MOUNTINFO_END\nXOOM_ANDROID44_SDCARD_RAM_SOURCE '+('verified' if fuse else 'unverified')+
          '\nXOOM_ANDROID44_POLICY_END_V1\nXOOM_ANDROID44_STAGES_BEGIN\n')
 if execute:policy+='XOOM_ANDROID44_STAGE exec_original_android_init\n'
 policy+='XOOM_ANDROID44_STAGES_END\nXOOM_ANDROID44_REPORT_DONE_V1\n'
 return body+policy.encode()

class AndroidReadOnly(unittest.TestCase):
 def result(self,data):return storage_result(data,GEOMETRY,62521344,storage_mode='android44-readonly')
 def test_radio_ram_overlays_and_readonly_pstore_from_pr23(self):
  ram=[('tmpfs',target,'tmpfs','rw,nosuid,nodev',f'0:{n}','/','rw')
       for n,target in enumerate(('/system/etc/wifi','/system/vendor/firmware','/system/lib/modules'),20)]
  pstore=('pstore','/sys/fs/pstore','pstore','ro,nosuid,nodev,noexec','0:30','/','ro')
  self.assertEqual(self.result(android_body(extras=ram+[pstore]))['state'],'geometry_matches_reference')
  for field,value in ((1,'/wrong-pstore'),(3,'rw'),(3,'ro,rw'),(5,'/subtree'),(6,'rw')):
   bad=list(pstore);bad[field]=value
   with self.subTest(field=field,value=value),self.assertRaises(ProtocolError):
    self.result(android_body(extras=[tuple(bad)]))
  with self.assertRaises(ProtocolError):self.result(android_body(extras=[pstore,pstore]))
  # /proc/mounts says ro while mountinfo says rw: no false read-only verdict.
  bad=android_body(extras=[pstore]).replace(b'/sys/fs/pstore ro,nosuid,nodev,noexec - pstore',b'/sys/fs/pstore rw - pstore')
  with self.assertRaises(ProtocolError):self.result(bad)
 def test_touch_profile_keeps_identical_readonly_policy(self):
  data=android_body().replace(b'4.4.147-wingray-android44\n',b'4.4.147-wingray-android44-touch\n')
  result=self.result(data)
  self.assertEqual(result['kernel_release'],'4.4.147-wingray-android44-touch')
  self.assertTrue(result['all_emmc_readonly_flags'])
  for suffix in (b'-other',b'-touch-other'):
   with self.assertRaises(ProtocolError):self.result(data.replace(b'-touch\n',suffix+b'\n'))
 def test_explicit_opt_in_and_complete_ram_system_evidence(self):
  data=android_body()
  with self.assertRaisesRegex(ProtocolError,'nonvirtual'):storage_result(data,GEOMETRY)
  result=self.result(data)
  self.assertEqual(result['state'],'geometry_matches_reference')
  self.assertEqual(result['storage_mode'],'android44-readonly')
  self.assertTrue(result['android_filesystems_mounted'])
  self.assertTrue(result['all_emmc_readonly_flags'])
  self.assertTrue(result['android_init_exec_attempted'])
  self.assertEqual(result['readonly_graphics_overlays'],['/system/lib/egl','/system/lib/hw'])
  self.assertNotIn('android_boot_completed',result) # Storage evidence cannot establish Android boot.
 def test_before_system_mount_is_a_diagnostic_snapshot(self):
  result=self.result(android_body(system=False,overlays=False,execute=False))
  self.assertFalse(result['android_filesystems_mounted'])
  self.assertFalse(result['android_init_exec_attempted'])
 def test_exact_release_board_and_all_readonly_flags_required(self):
  data=android_body()
  bad=[data.replace(b'4.4.147-wingray-android44',b'4.4.147-wingray-display'),
       data.replace(b'XOOM_ANDROID44_BOARD motorola,wingray',b'XOOM_ANDROID44_BOARD other'),
       data.replace(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 1\n',b''),
       data.replace(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 1',b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 0'),
       data.replace(b'XOOM_ANDROID44_BLOCK_RO mmcblk0p9 1',b'XOOM_ANDROID44_BLOCK_RO mmcblk0p8 1'),
       data.replace(b'XOOM_DISK mmcblk0 62521344 1',b'XOOM_DISK mmcblk0 62521344 0'),
       data.replace(b'XOOM_DISK mmcblk0 62521344 1\n',b''),
       data.replace(b'XOOM_ANDROID44_REPORT_DONE_V1\n',b''),
       storage_body()]
  for item in bad:
   with self.subTest(item=item[-120:]),self.assertRaises(ProtocolError):self.result(item)
 def test_writable_replayed_or_different_system_rejected(self):
  data=android_body()
  for before,after in [(b'/dev/mmcblk0p8',b'/dev/mmcblk0p9'),
                       (b'ro,nosuid,nodev,norecovery',b'rw,nosuid,nodev,norecovery'),
                       (b'ro,norecovery',b'rw,norecovery'),
                       (b'ro,nosuid,nodev,norecovery',b'ro,nosuid,nodev'),
                       (b'ro,norecovery',b'ro'),
                       (b'ro,nosuid,nodev,norecovery',b'ro,norecovery')]:
   with self.subTest(after=after),self.assertRaises(ProtocolError):self.result(data.replace(before,after))
  self.assertTrue(self.result(data.replace(b'norecovery',b'noload'))['android_filesystems_mounted'])
  self.assertTrue(self.result(data.replace(b'/dev/mmcblk0p8',b'/dev/block/mmcblk0p8'))['android_filesystems_mounted'])
 def test_ram_data_overlay_origin_and_init_stage_gates(self):
  data=android_body()
  bad=[data.replace(b'tmpfs /data tmpfs',b'/dev/mmcblk0p10 /data ext4'),
       data.replace(b'0:6 / /data',b'0:6 /old-data /data'),
       data.replace(b'0:5 /xoom-hw',b'0:9 /xoom-hw'),
       data.replace(b'/xoom-egl',b'/wrong-egl'),
       data.replace(b'/system/lib/hw tmpfs ro',b'/system/lib/hw tmpfs rw'),
       android_body(overlays=False),android_body(system=False,overlays=False),
       data.replace(b'XOOM_MOUNTS_END\n',b'/dev/mmcblk0p9 /cache-extra ext4 ro 0 0\nXOOM_MOUNTS_END\n'),
       data.replace(b'XOOM_MOUNTS_END\n',b'tmpfs /run tmpfs rw 0 0\nXOOM_MOUNTS_END\n')]
  for item in bad:
   with self.subTest(item=item[-100:]),self.assertRaises(ProtocolError):self.result(item)
 def test_mountinfo_must_match_but_order_is_not_significant(self):
  data=android_body()
  marker=b'XOOM_ANDROID44_MOUNTINFO_BEGIN\n';before,rest=data.split(marker);info,after=rest.split(b'XOOM_ANDROID44_MOUNTINFO_END\n')
  reordered=before+marker+b'\n'.join(reversed(info.splitlines()))+b'\n\nXOOM_ANDROID44_MOUNTINFO_END\n'+after
  self.assertEqual(self.result(reordered)['state'],'geometry_matches_reference')
  for item in [data.replace(b'0:5 / /run',b'bad / /run'),
               data.replace(b' - tmpfs tmpfs rw',b' bad tmpfs tmpfs rw',1),
               data.replace(b'XOOM_MOUNTS_END\n',b'XOOM_MOUNTS_END\nXOOM_MOUNTS_BEGIN\nXOOM_MOUNTS_END\n')]:
   with self.assertRaises(ProtocolError):self.result(item)
 def test_stacked_virtual_layers_allowed_but_stacked_system_is_rejected(self):
  data=android_body()
  virtual=[('proc','/proc','proc'),('sysfs','/sys','sysfs'),
           ('devtmpfs','/dev','devtmpfs'),('tmpfs','/dev','tmpfs'),
           ('devpts','/dev/pts','devpts'),('devpts','/dev/pts','devpts')]
  lines=''.join(f'{src} {target} {kind} rw 0 0\n' for src,target,kind in virtual).encode()
  info=''.join(f'{40+i} 1 0:{20+i} / {target} rw - {kind} {src} rw\n' for i,(src,target,kind) in enumerate(virtual)).encode()
  data=data.replace(b'XOOM_MOUNTS_END\n',lines+b'XOOM_MOUNTS_END\n')
  data=data.replace(b'XOOM_ANDROID44_MOUNTINFO_END\n',info+b'XOOM_ANDROID44_MOUNTINFO_END\n')
  self.assertEqual(self.result(data)['state'],'geometry_matches_reference')
  extra=b'/dev/mmcblk0p8 /system ext4 ro,nosuid,nodev,norecovery 0 0\n'
  data=data.replace(b'XOOM_MOUNTS_END\n',extra+b'XOOM_MOUNTS_END\n')
  data=data.replace(b'XOOM_ANDROID44_MOUNTINFO_END\n',b'60 1 179:8 / /system ro,nosuid,nodev,norecovery - ext4 /dev/mmcblk0p8 ro,norecovery\nXOOM_ANDROID44_MOUNTINFO_END\n')
  with self.assertRaisesRegex(ProtocolError,'stacked Android mount'):self.result(data)
 def test_expected_fuse_and_cgroups_are_only_opt_in(self):
  data=android_body(fuse=True)
  self.assertEqual(self.result(data)['state'],'geometry_matches_reference')
  for before,after in [(b'SDCARD_RAM_SOURCE verified',b'SDCARD_RAM_SOURCE unverified'),
                       (b'/mnt/shell/emulated',b'/mnt/media_rw/sdcard1'),
                       (b'0:8 /0 /storage',b'0:9 /0 /storage'),
                       (b'/dev/fuse',b'/dev/mmcblk0p10')]:
   with self.subTest(after=after),self.assertRaises(ProtocolError):self.result(data.replace(before,after))
  data=android_body()
  data=data.replace(b'XOOM_MOUNTS_END\n',b'none /acct cgroup rw,cpuacct 0 0\nXOOM_MOUNTS_END\n')
  data=data.replace(b'XOOM_ANDROID44_MOUNTINFO_END\n',b'35 1 0:10 / /acct rw - cgroup none rw,cpuacct\nXOOM_ANDROID44_MOUNTINFO_END\n')
  self.assertEqual(self.result(data)['state'],'geometry_matches_reference')
  with self.assertRaises(ProtocolError):self.result(data.replace(b'/acct',b'/unexpected'))
  with self.assertRaises(ProtocolError):storage_result(data,GEOMETRY)
 def test_mode_and_policy_duplicates_are_rejected(self):
  with self.assertRaises(ProtocolError):storage_result(storage_body(),GEOMETRY,storage_mode='automatic')
  data=android_body()
  with self.assertRaises(ProtocolError):self.result(data+b'XOOM_ANDROID44_POLICY_BEGIN_V1\nXOOM_ANDROID44_POLICY_END_V1\n')
  with self.assertRaises(ProtocolError):storage_result(data,GEOMETRY,70000000,storage_mode='android44-readonly')

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
