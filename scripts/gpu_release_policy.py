"""Fixed GPU release evidence checks, shared with offline negative controls."""
import hashlib,re

def validate_waiting_payload(payload):
    for token in (b'XOOM_GPU_RENDER_WAIT_USB_GATE', b'XOOM_GPU_RENDER_DEVICES_READY',
                  b'XOOM_GPU_PROPERTY_WORKSPACE_PRESENT'):
        assert token in payload, token
    for token in (b'XOOM_GPU_RENDER_EXIT ', b'XOOM_GPU_RENDER_GATE_TIMEOUT',
                  b'XOOM_GPU_RENDER_PASS', b'XOOM_GPU_RENDER_FAILED'):
        assert token not in payload, token
    assert re.search(rb'^XOOM_GPU_KERNEL 4\.4\.147-wingray-gpu-trace\r?$',payload,re.M)

def validate_release_evidence(state,manifest,status,payload,image):
    assert state['original_restoration_pending'] and state['rendering_enabled']
    assert state['stage']=='candidate-observation'
    assert not state.get('gpu_probe_released_by_agent') and not state.get('gpu_release_pending')
    assert state['candidate_sha256']==manifest['sha256']==hashlib.sha256(image).hexdigest()
    assert manifest['deferred_probe'] and manifest['builtin_runtime'] and manifest['rendering_enabled']
    assert manifest['trace_cookie'] in ('0x584d0056','0x584d0057')
    assert status['state']=='verified' and status['report_integrity']=='verified'
    assert status['storage_state']=='geometry_matches_reference'
    assert hashlib.sha256(payload).hexdigest()==status['sha256']
    validate_waiting_payload(payload)
