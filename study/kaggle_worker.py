"""Private Kaggle batch worker. Input is injected by the local launcher.

No credential, inference endpoint, public dataset or persistent server is used.
Only result.zip and a bounded receipt leave the temporary working directory.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run(payload, expected_hash):
    started = time.monotonic()
    output = Path('/kaggle/working')
    stage = 'hardware'
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('Requested GPU is unavailable')
        hardware = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
        with tempfile.TemporaryDirectory(prefix='study-mineru-') as td:
            td = Path(td)
            source = td/'page.pdf'
            data = base64.b64decode(payload, validate=True)
            if len(data) > 2_000_000 or hashlib.sha256(data).hexdigest() != expected_hash:
                raise ValueError('Input integrity failure')
            source.write_bytes(data)
            # Keep input, model cache, installation and detailed logs outside
            # Kaggle's downloadable output folder. No secrets are injected.
            env = {**os.environ, 'MINERU_HOME':str(td/'mineru'),
                   'HF_HOME':str(td/'hf'), 'HF_HUB_DISABLE_XET':'1',
                   'MINERU_MODEL_SMALL_BACKEND':'torch',
                   'MINERU_MODEL_VLM_ENGINE':'llama-cpp', 'OMP_NUM_THREADS':'4'}
            env.pop('MINERU_CONFIG', None)
            for name in list(env):
                if name.startswith('MINERU_') and any(x in name for x in ('API','SERVER','REMOTE')):
                    env.pop(name, None)
            log = td/'runtime.log'
            def command(args, timeout):
                with log.open('ab') as handle:
                    subprocess.run(args, env=env, cwd=td, stdout=handle,
                                   stderr=subprocess.STDOUT, check=True, timeout=timeout)
            stage = 'venv'
            # Kaggle images can omit ensurepip. Reuse the image's pip module
            # inside an isolated venv instead of bootstrapping system packages.
            command([sys.executable,'-m','venv','--system-site-packages','--without-pip',str(td/'venv')],60)
            python = str(td/'venv/bin/python')
            stage = 'install'
            command([python,'-m','pip','install','--disable-pip-version-check',
                     'mineru[torch]==4.1.3','pymupdf==1.26.7'],600)
            cli = str(td/'venv/bin/mineru-kit')
            stage = 'models'
            command([cli,'models','download','--tier','standard','--small-backend','torch',
                     '--vlm-engine','llama-cpp','--source','huggingface'],600)
            command([cli,'models','verify','--tier','standard','--small-backend','torch',
                     '--vlm-engine','llama-cpp'],60)
            env.update(MINERU_MODEL_SOURCE='local', HF_HUB_OFFLINE='1')
            stage = 'parse'
            result = td/'result.zip'
            command([cli,'parse',str(source),'--tier','standard','--ocr-mode','auto',
                     '--format','zip','-o',str(result)],240)
            if not result.is_file() or result.stat().st_size > 40_000_000:
                raise ValueError('Output limit exceeded')
            archive = result.read_bytes()
            receipt = {'engine':'mineru-4.1.3-standard-kaggle-gpu',
                       'input_sha256':expected_hash,'output_sha256':hashlib.sha256(archive).hexdigest(),
                       'seconds':round(time.monotonic()-started,2),'cloud_upload':True,
                       'original_pages_uploaded':1,'hardware':hardware,
                       'small_model_backend':'torch','vlm_engine':'llama-cpp',
                       'warning':'GPU allocation does not mean every parser stage uses the GPU.'}
            (output/'result.zip').write_bytes(archive)
            (output/'receipt.json').write_text(json.dumps(receipt))
        print('Study page prepared. Download and validate the result locally.')
    except Exception as exc:
        diagnostic = ''
        if stage in {'venv','install','models'} and 'log' in locals() and log.exists():
            diagnostic = log.read_text(errors='replace')[-2400:]
        (output/'failure.json').write_text(json.dumps({'stage':stage,'error_type':type(exc).__name__,
                                                     'diagnostic':diagnostic}))
        print('Study processing failed at '+stage+'. Original and previous local extraction are preserved.')
        raise SystemExit(1)
