#!/usr/bin/env python3
"""Duplicate UUID is not identity when fixed p9 geometry/evidence are checked."""
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cache_profile import approved_cache_token
with tempfile.TemporaryDirectory() as d:
 p=Path(d);uuid='57f8f4bcabf4655fbf67946fc0f9f25b'
 meta={'uuid':uuid,'compat':28,'incompat':66,'ro_compat':19}
 (p/'filesystem.json').write_text(json.dumps(meta))
 with patch('cache_profile.validate_host_report',return_value={'sha256':'a'*64}) as verify:
  assert approved_cache_token(p/'host-inspection.json',uuid).startswith(uuid.encode()+b'\n')
  assert verify.call_args.kwargs=={'partition':'cache'}
 meta['uuid']='0'*32;(p/'filesystem.json').write_text(json.dumps(meta))
 with patch('cache_profile.validate_host_report',return_value={'sha256':'a'*64}):
  try:approved_cache_token(p/'host-inspection.json',uuid)
  except ValueError:pass
  else:raise AssertionError('zero UUID accepted')
print('PASS cache evidence purpose required; duplicate UUID allowed; zero UUID blocked')
