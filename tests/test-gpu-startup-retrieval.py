#!/usr/bin/env python3
"""Exercise readback orchestration with a fake ADB; never maps real memory."""
from pathlib import Path
import base64,hashlib,importlib.util,json,struct,subprocess,sys,tempfile,types
r=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('retrieve',r/'scripts/retrieve-gpu-startup-trace.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original_run=m.subprocess.run;original_argv=sys.argv;original_root=m.ROOT;original_reader_sha=m.READER_SHA
old_gpu=sys.modules.get('gpu_test');sys.modules['gpu_test']=types.SimpleNamespace(validate_artifacts=lambda p,**kw:None,startup_cookie=lambda p:0x584d0049)
try:
 for case in ['success','wrong-kernel','occupied-page','wrong-hash','wrong-map','wrong-image','stale','unstable','new-fault']:
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);out=root/'artifacts/attempt';out.mkdir(parents=True);kernel=root/'kernel';kernel.mkdir();(kernel/'System.map').write_text('c0123450 t test_init\n')
   decoder=root/'scripts';decoder.mkdir();(decoder/'decode-gpu-startup-trace.py').write_bytes((r/'scripts/decode-gpu-startup-trace.py').read_bytes())
   reader=root/'artifacts/trace-reader/mmap-snapshot';reader.parent.mkdir();reader.write_bytes(b'fake reader (not executable)')
   m.ROOT=root;m.READER_SHA=hashlib.sha256(reader.read_bytes()).hexdigest()
   (kernel/'zImage-dtb').write_bytes(b'fake compiled image')
   (out/'test-state-private.json').write_text(json.dumps({'full_original_hashes_verified':True,'original_restoration_pending':False,'candidate_sha256':'fake-candidate'}))
   (out/'kernel-artifact-verification.json').write_text(json.dumps({'compiled_outputs_match':True,'candidate_sha256':'fake-candidate','kernel_sha256':hashlib.sha256((kernel/'zImage-dtb').read_bytes()).hexdigest(),'system_map_sha256':hashlib.sha256((kernel/'System.map').read_bytes()).hexdigest()}))
   if case=='wrong-map':(kernel/'System.map').write_text('c0123450 t wrong_map\n')
   if case=='wrong-image':(kernel/'zImage-dtb').write_bytes(b'wrong image')
   commands=[];mapped=0;removed=False;dmesg_reads=0
   def run(args,**kw):
    global mapped,removed,dmesg_reads
    commands.append(args)
    assert args[:3]==['/usr/bin/adb','-s','fake-serial']
    if args[3]=='push':return subprocess.CompletedProcess(args,0,b'',b'')
    assert args[3]=='shell';cmd=args[4]
    if cmd.startswith('getprop ro.product.device;'):data='wingray\n'+('wrong' if case=='wrong-kernel' else '2.6.39.4-ElementalX-Xoom-2.1+')+'\nuid=0(root)\n1\n'
    elif cmd=='cat /proc/sys/kernel/random/boot_id':data='unchanged-boot-id\n'
    elif cmd=='getprop sys.boot_completed':data='1\n'
    elif cmd.startswith('printf abc'):data='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  -\n'
    elif cmd.startswith('cat /sys/block/'):
     data=str(8388608//512 if 'mmcblk0p7' in cmd else 12582912//512)+'\n'
    elif cmd.startswith('/system/xbin/busybox sha256sum /dev/block/'):
     name='boot' if cmd.endswith('mmcblk0p7') else 'recovery';part,_,sha=m.ORIGINAL[name];data=('0'*64 if case=='wrong-hash' else sha)+'  /dev/block/'+part+'\n'
    elif cmd=='cat /proc/iomem':data='1ff00000-1fffffff : ram_console\n'+('1fe00000-1fe00fff : System RAM\n' if case=='occupied-page' else '')
    elif cmd=='dmesg':
     dmesg_reads+=1;data='baseline log\n'+('Oops: new fault\n' if case=='new-fault' and dmesg_reads>1 else '')
    elif cmd.startswith('mkdir /dev/') or cmd.startswith('chmod 500 /dev/'):data=''
    elif cmd.startswith('/system/xbin/busybox sha256sum /dev/xoom-'):data=m.READER_SHA+'  reader\n'
    elif cmd.endswith('/reader') and cmd.startswith('/dev/xoom-'):data='OFFLINE DEFAULT: no device opened\n'
    elif '--read-reserved-trace' in cmd:
     mapped+=1;assert mapped==1
     words=[0]*32;words[:3]=[0x58534d50,1,0x584d0049]
     if case=='stale':words[2]=0x584d0037
     payload=struct.pack('<32I',*words)+b'\nXOOM_MMAP_RC=0\n'
     if case=='unstable':payload=b'unstable snapshot withheld\n\nXOOM_MMAP_RC=6\n'
     data=base64.b64encode(payload).decode()+'\n'
    elif cmd.startswith('rm /dev/xoom-'):removed=True;data=''
    elif cmd.startswith('if [ -e /dev/xoom-'):assert removed;data='REMOVED\n'
    else:raise AssertionError(cmd)
    return subprocess.CompletedProcess(args,0,data.encode(),b'')
   m.subprocess.run=run;sys.argv=['retrieve','--serial','fake-serial','--attempt-dir',str(out),'--kernel-dir',str(kernel)]
   try:m.main()
   except AssertionError:
    assert case!='success',case
   else:assert case=='success',case
   if case in ['wrong-kernel','occupied-page','wrong-hash','wrong-map','wrong-image']:assert not mapped and not removed
   else:assert mapped==1 and removed and (out/'trace-reader-cleanup.txt').exists()
   assert not any(' reboot' in str(c) or ' flash' in str(c) or 'devmem' in str(c) for c in commands)
   print('PASS mocked retrieval:',case)
finally:
 m.subprocess.run=original_run;sys.argv=original_argv;m.ROOT=original_root;m.READER_SHA=original_reader_sha
 if old_gpu is None:sys.modules.pop('gpu_test',None)
 else:sys.modules['gpu_test']=old_gpu
