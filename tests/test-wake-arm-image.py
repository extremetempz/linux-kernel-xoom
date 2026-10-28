#!/usr/bin/env python3
"""Verify the blocked PM image policy and actual fixed test/USB script."""
from pathlib import Path
import argparse,base64,hashlib,os,pty,select,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pm_preparation_profile import blocked_pm
from diagnostic_protocol import handshake,write_request
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--config',type=Path,required=True)
p.add_argument('--runtime',type=Path)
a=p.parse_args();cfg=a.config.read_text();assert blocked_pm(cfg)
for key in ('MOTOROLA_WINGRAY_PM_PREPARE','MFD_CPCAP_WINGRAY_WAKE_ARM_TEST',
            'MFD_CPCAP_WINGRAY_IRQ_TEST','SUSPEND','PM','HOTPLUG_CPU',
            'TEGRA_GRHOST_WINGRAY_GPU_TEST'):
    bad=cfg.replace('CONFIG_'+key+'=y\n','# CONFIG_'+key+' is not set\n')
    try: blocked_pm(bad)
    except AssertionError: pass
    else: raise AssertionError('Accepted missing '+key)
for key in ('PM_AUTOSLEEP','PM_WAKELOCKS','CPU_FREQ','CPU_IDLE','HIBERNATION',
            'FB_TEGRA_WINGRAY_DC_RESUME_TEST'):
    try: blocked_pm(cfg+'\nCONFIG_'+key+'=y\n')
    except AssertionError: pass
    else: raise AssertionError('Accepted forbidden '+key)
old=(ROOT.parent/'dc-hang-85/artifacts/dc85-runtime/kernel.config')
if old.exists(): assert not blocked_pm(old.read_text())
BB='/usr/bin/busybox'
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp);devices=tmp/'devices';device=devices/'spi-test';device.mkdir(parents=True)
    arm=device/'wingray_wake_arm';arm.write_text('0\n');mode=tmp/'mode';mode.write_text('ok')
    wrapper=tmp/'bb'
    wrapper.write_text('''#!/bin/sh
if [ "$1" = id ] && [ "$2" = -u ]; then echo 0; exit 0; fi
if [ "$1" = cat ] && [ "$2" = "'''+str(arm)+'''" ]; then
 v=$('''+BB+''' cat "$2")
 m=$('''+BB+''' cat "'''+str(mode)+'''" )
 [ "$m" != prearmed ] || v=1
 [ "$m" != mismatch ] || v=0
 echo "owned=$v parent_wake=$v last_error=0 cleanup_error=0 hardware_wake_validated=0 soc_suspend=blocked"
 exit 0
fi
exec '''+BB+''' "$@"
''');wrapper.chmod(0o755)
    script=tmp/'wake';source=(ROOT/'diagnostic/wake-arm-cycle.sh').read_text().replace('BB=/bin/busybox','BB='+str(wrapper)).replace('/sys/bus/spi/devices/',str(devices)+'/');script.write_text(source);script.chmod(0o755)
    result=subprocess.run([BB,'sh',str(script)],capture_output=True,check=True)
    assert b'WAKETEST_PROCESS_RC 0\n' in result.stdout and arm.read_text().strip()=='0'
    mode.write_text('prearmed');arm.write_text('original\n')
    result=subprocess.run([BB,'sh',str(script)],capture_output=True)
    assert result.returncode and arm.read_text()=='original\n' and b'WAKETEST_ARM_RC' not in result.stdout
    mode.write_text('mismatch');arm.write_text('0\n')
    result=subprocess.run([BB,'sh',str(script)],capture_output=True)
    assert result.returncode and b'WAKETEST_CLEANUP_RC 0\n' in result.stdout and arm.read_text().strip()=='0'
    arm.unlink();result=subprocess.run([BB,'sh',str(script)],capture_output=True)
    assert result.returncode and b'WAKETEST_MISSING_OR_AMBIGUOUS' in result.stdout
    # Actual USB server: frame a successful and a failed fixed helper output.
    fixture=tmp/'fixture';body=b'XOOM_WAKE_ARM_TEST_V1\nWAKETEST_PROCESS_RC 0\nXOOM_WAKE_ARM_TEST_END\n';fixture.write_bytes(body)
    helper=tmp/'helper';helper.write_text('#!/bin/sh\n'+BB+' cat '+str(fixture)+'\nexit 1\n');helper.chmod(0o755)
    server=tmp/'server';server.write_text((ROOT/'diagnostic/server.sh').read_text().replace('/bin/busybox',BB).replace('/bin/wake-arm-cycle',str(helper)).replace('/run/',str(tmp)+'/'))
    master,slave=pty.openpty();os.set_blocking(master,False)
    process=subprocess.Popen([BB,'sh',str(server)],stdin=slave,stdout=slave,stderr=subprocess.PIPE)
    try:
        for value,nonce in [(0,'9'*32),(1,'8'*32)]:
            body=('XOOM_WAKE_ARM_TEST_V1\nWAKETEST_PROCESS_RC '+str(value)+'\nXOOM_WAKE_ARM_TEST_END\n').encode()
            fixture.write_bytes(body)
            handshake(master,nonce,timeout=5);write_request(master,'WAKETEST',nonce)
            wire=bytearray();deadline=time.monotonic()+5
            end=b'XOOM_WAKETEST_END_V1 '+nonce.encode()
            while time.monotonic()<deadline and end not in wire:
                if select.select([master],[],[],0.2)[0]:wire.extend(os.read(master,65536))
            expected=b'XOOM_WAKETEST_V1 '+nonce.encode()+b' '+str(len(body)).encode()+b' '+hashlib.sha256(body).hexdigest().encode()+b'\n'
            assert expected in wire and end in wire and base64.b64encode(body) in wire.replace(b'\n',b'')

    finally:
        process.terminate();process.wait(timeout=5);os.close(master);os.close(slave)
        assert process.stderr.read()==b'';process.stderr.close()
if a.runtime:
    from android_gpu import validate_artifacts
    validate_artifacts(a.runtime,require_framebuffer_translation=True)
    # Existing no-PM profile must still pass the same artifact validator.
    old=ROOT.parent/'dc-hang-85/artifacts/dc85-runtime'
    if old.exists(): validate_artifacts(old,require_framebuffer_translation=True)
subprocess.run([sys.executable,str(ROOT/'scripts/run-wake-arm-test.py'),'--help'],check=True,stdout=subprocess.DEVNULL)
print('PASS blocked-PM policy, actual one-pair helper/cleanup and nonce/hash USB framing; physical wake untested')
