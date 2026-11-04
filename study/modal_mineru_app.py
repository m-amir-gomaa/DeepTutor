"""Private personal-study OCR RPC. No web endpoint, public guest ledger or GPU.

Uses the same MinerU Standard/ONNX/llama.cpp release as local preparation.
CPU is deliberate: reproducible base wheels, bounded cost, no GPU cold start.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import modal

if os.environ.get('STUDY_MODAL_POLICY'):
    POLICY=json.loads(os.environ['STUDY_MODAL_POLICY'])
else:
    # Only the deployment client reads its local non-secret configuration.
    # The worker receives an explicit policy through the immutable image env.
    import study_settings
    POLICY=study_settings.load()['modal']
APP_NAME = POLICY['app']
app = modal.App(APP_NAME, tags={'purpose': 'personal-study'})
image = (modal.Image.debian_slim(python_version='3.12')
         .apt_install('libgl1', 'libglib2.0-0', 'libgomp1')
         .uv_pip_install('mineru==4.1.3', 'pymupdf==1.26.7')
         .env({'MINERU_HOME': '/opt/mineru', 'MINERU_MODEL_BASE_DIR': '/opt/mineru/models',
               'MINERU_MODEL_SMALL_BACKEND': 'onnx', 'MINERU_MODEL_ONNX_DEVICE': 'cpu',
               'MINERU_MODEL_VLM_ENGINE': 'llama-cpp', 'OMP_NUM_THREADS': '4',
               'OPENBLAS_NUM_THREADS': '4', 'HF_HUB_DISABLE_XET': '1'})
         .run_commands('mineru-kit models download --tier standard --small-backend onnx --vlm-engine llama-cpp --source huggingface',
                       'mineru-kit models verify --tier standard --small-backend onnx --vlm-engine llama-cpp')
         .env({'MINERU_MODEL_SOURCE': 'local', 'HF_HUB_OFFLINE': '1',
               'STUDY_MODAL_POLICY':json.dumps({k:POLICY[k] for k in ['app','enabled','reservation_limit_usd','credit_ceiling_usd','reserve_usd']})})
         .add_local_file(Path(__file__).with_name('modal_admission.py'), '/root/modal_admission.py', copy=True))
ledger = modal.Volume.from_name(APP_NAME+'-admission-v1', create_if_missing=True)


@app.function(image=image, volumes={'/admission': ledger}, cpu=(4, 4), memory=(16384, 16384),
              timeout=210, startup_timeout=120, max_containers=1, min_containers=0,
              buffer_containers=0, scaledown_window=5, retries=0)
def parse_page(pdf_bytes: bytes, job_id: str) -> dict:
    """One page, 12MB input, 180s parser. Reservations are not billing promises."""
    import pymupdf
    if not POLICY['enabled']:raise ValueError('Cloud OCR is disabled. The owner must configure and deploy its policy first.')
    if not isinstance(pdf_bytes, bytes) or len(pdf_bytes) > 12_000_000 or not pdf_bytes.startswith(b'%PDF-'):
        raise ValueError('Use a single-page PDF smaller than 12 MB.')
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
        raise ValueError('Invalid job identifier.')
    with pymupdf.open(stream=pdf_bytes, filetype='pdf') as doc:
        if doc.page_count != 1 or doc.needs_pass:
            raise ValueError('Use one unlocked physical PDF page.')
    # Fail closed on unavailable billing. Keep a dollar buffer below free credit;
    # $0 net dashboard limit remains the outer, owner-confirmed control.
    summary = modal.Workspace.from_context().billing.summary()
    cycle = summary.start.strftime('%Y-%m')
    ledger.reload()
    path = Path('/admission/reservations.json')
    from modal_admission import admit
    state = admit(json.loads(path.read_text()) if path.exists() else None, cycle,
                  summary.metered_cost, summary.billed_cost, job_id,
                  hashlib.sha256(pdf_bytes).hexdigest(), time.time(),
                  limit_usd=POLICY['reservation_limit_usd'],credit_ceiling_usd=POLICY['credit_ceiling_usd'],reserve_usd=POLICY['reserve_usd'])
    tmp = path.with_suffix('.tmp');tmp.write_text(json.dumps(state));os.replace(tmp, path)
    ledger.commit()  # Admission must persist before inference.
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='study-page-') as td:
        td = Path(td);source = td/'page.pdf';output = td/'result.zip';source.write_bytes(pdf_bytes)
        result = subprocess.run(['mineru-kit', 'parse', str(source), '--tier', 'standard',
                                 '--ocr-mode', 'auto', '--format', 'zip', '-o', str(output)],
                                capture_output=True, timeout=180)
        if result.returncode or not output.exists():
            raise RuntimeError('Modal MinerU failed. The source and previous local extraction are preserved.')
        data = output.read_bytes()
        if len(data) > 40_000_000:
            raise RuntimeError('Parser output exceeds the bounded response size.')
    return {'archive': data, 'receipt': {'job_id': job_id, 'engine': 'mineru-4.1.3-standard-modal-cpu',
            'seconds': round(time.monotonic()-started, 2), 'cycle': cycle, 'reserved_usd': POLICY['reserve_usd'],
            'monthly_reservation_limit_usd': POLICY['reservation_limit_usd'], 'cloud_upload': True, 'original_pages_uploaded': 1,
            'input_sha256': hashlib.sha256(pdf_bytes).hexdigest(), 'output_sha256': hashlib.sha256(data).hexdigest()}}
