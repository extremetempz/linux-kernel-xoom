#!/usr/bin/env python3
"""Reject stale/finished/nonmatching GPU-release evidence before serial writes."""
from pathlib import Path
import copy,hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gpu_release_policy import validate_release_evidence,validate_waiting_payload
payload=b'XOOM_GPU_KERNEL 4.4.147-wingray-gpu-trace\nXOOM_GPU_RENDER_WAIT_USB_GATE\nXOOM_GPU_RENDER_DEVICES_READY\nXOOM_GPU_PROPERTY_WORKSPACE_PRESENT\n'
image=b'candidate';sha=hashlib.sha256(image).hexdigest()
s={'original_restoration_pending':True,'rendering_enabled':True,'stage':'candidate-observation','candidate_sha256':sha}
m={'sha256':sha,'deferred_probe':True,'builtin_runtime':True,'rendering_enabled':True,'trace_cookie':'0x584d0057'}
t={'state':'verified','report_integrity':'verified','storage_state':'geometry_matches_reference','sha256':hashlib.sha256(payload).hexdigest()}
validate_release_evidence(s,m,t,payload,image)
for target,key,value in [(0,'original_restoration_pending',False),(0,'gpu_release_pending',True),(0,'gpu_probe_released_by_agent',True),(0,'stage','original-restored-and-verified'),(0,'candidate_sha256','wrong'),(1,'trace_cookie','0x584d0055'),(1,'builtin_runtime',False),(1,'deferred_probe',False),(2,'state','failed'),(2,'storage_state','partition_set_mismatch'),(2,'sha256','wrong')]:
 args=copy.deepcopy([s,m,t]);args[target][key]=value
 try:validate_release_evidence(*args,payload,image)
 except AssertionError:pass
 else:raise AssertionError((key,value))
for token in (b'XOOM_GPU_RENDER_EXIT 0',b'XOOM_GPU_RENDER_GATE_TIMEOUT',b'XOOM_GPU_RENDER_PASS',b'XOOM_GPU_RENDER_FAILED'):
 try:validate_waiting_payload(payload+token+b'\n')
 except AssertionError:pass
 else:raise AssertionError(token)
try:validate_waiting_payload(payload.replace(b'4.4.147-wingray-gpu-trace',b'2.6.39'))
except AssertionError:pass
else:raise AssertionError('wrong kernel accepted')
print('PASS release evidence: matching deferred image only, verified storage/report, waiting current runtime, no previous release or completed probe')
