#!/usr/bin/env python3
"""Exercise the actual fixed freezer helper and USB framing on fixtures."""
from pathlib import Path
import base64,hashlib,os,pty,select,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from diagnostic_protocol import handshake,write_request
BB='/usr/bin/busybox'
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);node=p/'test';counter=p/'count';mode=p/'mode';counter.write_text('0');mode.write_text('ok')
 status=lambda n,rc=0:f'completed={n} last_result={rc} device_suspend=0 cpu_sleep=0 ordinary_sleep=blocked\n'
 node.write_text(status(0));wrapper=p/'bb'
 wrapper.write_text('''#!/bin/sh
if [ "$1" = id ] && [ "$2" = -u ]; then echo 0; exit 0; fi
if [ "$1" = cat ] && [ "$2" = "'''+str(node)+'''" ]; then
 v=$('''+BB+''' cat "$2")
 if [ "$v" = 1 ]; then
  n=$('''+BB+''' cat "'''+str(counter)+'''" )
  rc=0
  if [ "$('''+BB+''' cat "'''+str(mode)+'''" )" = fail ]; then rc=-5; else n=$((n + 1)); fi
  echo "$n" > "'''+str(counter)+'''"
  echo "completed=$n last_result=$rc device_suspend=0 cpu_sleep=0 ordinary_sleep=blocked" > "$2"
 fi
fi
exec '''+BB+''' "$@"
''');wrapper.chmod(0o755)
 helper=p/'freezer';helper.write_text((ROOT/'diagnostic/freezer-cycle.sh').read_text().replace('BB=/bin/busybox','BB='+str(wrapper)).replace('/sys/power/wingray_freezer_test',str(node)));helper.chmod(0o755)
 result=subprocess.run([BB,'sh',str(helper)],capture_output=True,check=True)
 assert b'FREEZERTEST_COUNTER_ADVANCED_1' in result.stdout and b'FREEZERTEST_PROCESS_RC 0' in result.stdout
 assert node.read_text()==status(1)
 counter.write_text('3');node.write_text(status(3));result=subprocess.run([BB,'sh',str(helper)],capture_output=True,check=True);assert node.read_text()==status(4)
 mode.write_text('fail');result=subprocess.run([BB,'sh',str(helper)],capture_output=True)
 assert result.returncode and b'last_result=-5' in result.stdout and b'FREEZERTEST_PROCESS_RC 1' in result.stdout
 assert b'FREEZERTEST_COUNTER_ADVANCED_1' not in result.stdout
 # A previous failed state cannot silently trigger another write.
 before=node.read_bytes();result=subprocess.run([BB,'sh',str(helper)],capture_output=True)
 assert result.returncode and node.read_bytes()==before and b'FREEZERTEST_WRITE_RC' not in result.stdout
 node.unlink();result=subprocess.run([BB,'sh',str(helper)],capture_output=True);assert result.returncode and b'FREEZERTEST_MISSING' in result.stdout
 fixture=p/'fixture';fixed=p/'fixed';fixed.write_text('#!/bin/sh\n'+BB+' cat '+str(fixture)+'\nexit 1\n');fixed.chmod(0o755)
 server=p/'server';server.write_text((ROOT/'diagnostic/server.sh').read_text().replace('/bin/busybox',BB).replace('/bin/freezer-cycle',str(fixed)).replace('/run/',str(p)+'/'))
 master,slave=pty.openpty();os.set_blocking(master,False)
 process=subprocess.Popen([BB,'sh',str(server)],stdin=slave,stdout=slave,stderr=subprocess.PIPE)
 try:
  for rc,nonce in ((0,'7'*32),(1,'6'*32)):
   body=('XOOM_FREEZER_TEST_V1\nFREEZERTEST_PROCESS_RC '+str(rc)+'\nXOOM_FREEZER_TEST_END\n').encode();fixture.write_bytes(body)
   handshake(master,nonce,timeout=5);write_request(master,'FREEZERTEST',nonce)
   wire=bytearray();deadline=time.monotonic()+5;end=b'XOOM_FREEZERTEST_END_V1 '+nonce.encode()
   while time.monotonic()<deadline and end not in wire:
    if select.select([master],[],[],0.2)[0]:wire.extend(os.read(master,65536))
   header=b'XOOM_FREEZERTEST_V1 '+nonce.encode()+b' '+str(len(body)).encode()+b' '+hashlib.sha256(body).hexdigest().encode()+b'\n'
   assert header in wire and end in wire and base64.b64encode(body) in wire.replace(b'\n',b'')
 finally:
  process.terminate();process.wait(timeout=5);os.close(master);os.close(slave)
  assert process.stderr.read()==b'';process.stderr.close()
source=(ROOT/'diagnostic/freezer-cycle.sh').read_text()
assert '/sys/power/state' not in source and 'echo 1 > "$TEST"' in source
subprocess.run([sys.executable,str(ROOT/'scripts/run-freezer-test.py'),'--help'],check=True,stdout=subprocess.DEVNULL)
print('PASS actual fixed freezer helper/counter/error handling and success/failure USB framing; no hardware freeze')
