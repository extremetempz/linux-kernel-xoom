"""Independent p9 evidence gate; no mount, repair, policy change or device access."""
import json
from pathlib import Path
from storage_host_evidence import validate_host_report

def approved_cache_token(report, data_uuid):
    result=validate_host_report(Path(report),partition='cache')
    metadata=json.loads((Path(report).resolve().parent/'filesystem.json').read_text())
    if metadata['uuid']=='0'*32:
        raise ValueError('Cache must have a nonzero filesystem UUID')
    features=''.join(metadata[key].to_bytes(4,'little').hex() for key in ('compat','incompat','ro_compat'))
    return (metadata['uuid']+'\n'+features+'\n'+result['sha256']+'\n').encode('ascii')
