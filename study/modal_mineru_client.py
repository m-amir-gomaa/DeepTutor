"""Isolated Modal SDK subprocess. Never returns credentials or provider payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid
import modal
import os
import study_settings

def wait_for_job(function,payload,job_id,timeout=240):
    """Bound queue + startup + processing; cancel this input if the wait fails."""
    call=function.spawn(payload,job_id)
    try:return call.get(timeout=timeout)
    except BaseException:
        try:call.cancel()
        except Exception:pass
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
    payload=Path(a.source).read_bytes()
    if len(payload)>12_000_000 or not payload.startswith(b'%PDF-'):
        raise ValueError('Use a single PDF page smaller than 12 MB.')
    conf=study_settings.load()['modal']
    if not conf['enabled']:raise ValueError('Modal processing is disabled in this installation.')
    if conf['profile']:os.environ['MODAL_PROFILE']=conf['profile']
    result=wait_for_job(modal.Function.from_name(conf['app'],'parse_page'),payload,uuid.uuid4().hex)
    data=result['archive'];receipt=result['receipt']
    if not isinstance(data,bytes) or len(data)>40_000_000 or hashlib.sha256(data).hexdigest()!=receipt['output_sha256']:
        raise ValueError('Modal result integrity check failed.')
    if receipt['input_sha256']!=hashlib.sha256(payload).hexdigest():
        raise ValueError('Modal input provenance check failed.')
    target=Path(a.output)
    with target.open('xb') as f:f.write(data)
    target.chmod(0o600)
    print(json.dumps(receipt))

if __name__=='__main__':
    try:main()
    except Exception as e:
        # RPC exceptions can include remote traceback and private filesystem names.
        print(json.dumps({'error':'Personal Modal processing unavailable; original and previous extraction preserved. Use local processing or inspect the owner Modal dashboard.','error_type':type(e).__name__}),file=sys.stderr)
        sys.exit(1)
