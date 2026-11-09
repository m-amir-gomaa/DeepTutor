"""One-account personal-study Kaggle jobs; no automatic retries or paid fallback."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

import library
import study_settings


def cli(args, timeout=40):
    executable = study_settings.tool('kaggle')
    if not executable:
        raise RuntimeError('Install the official Kaggle CLI and authorize your own account.')
    try:
        result = subprocess.run([executable,'-W',*args],capture_output=True,text=True,timeout=timeout)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError('Kaggle did not respond. Check the saved job before retrying; it may still be running.') from None
    if result.returncode:
        raise RuntimeError('Kaggle rejected the request. Check account authorization, verification and the private notebook page. No fallback ran.')
    return result.stdout


def status(check=False):
    conf = study_settings.load()['kaggle']
    result = {'installed':bool(study_settings.tool('kaggle')),'enabled':conf['enabled'],
              'username':conf['username'],'checked':check,'authorized':None,
              'quota':None,'credentials_returned':False,
              'login_command':'kaggle auth login','terms_url':'https://www.kaggle.com/terms',
              'policy':'One account, personal non-commercial study. Batch notebooks may queue; no GPU or quota guarantee.'}
    if check:
        try:
            quota = json.loads(cli(['quota','--format','json'],timeout=25))
            result.update(authorized=True,quota=[{k:r.get(k) for k in ['resource','used','remaining','total','refreshAt']} for r in quota])
        except (RuntimeError,ValueError,TypeError):
            result.update(authorized=False,error='Kaggle quota unavailable. Authorize the configured account and check again.')
    return result


def job_path(job_id):
    if not re.fullmatch('[a-f0-9]{32}',job_id):
        raise ValueError('Invalid study job ID')
    return library.CONTROL/'kaggle-jobs'/job_id


def save(path, data):
    library.write_json(path/'job.json',data)


def view(data):
    return {k:data.get(k) for k in ['id','vault','source_sha256','state','kernel','submitted_at','max_seconds','cleanup_pending']}


def jobs(slug):
    library.vault(slug)
    root = library.CONTROL/'kaggle-jobs'
    return sorted([view(json.loads(p.read_text())) for p in root.glob('*/job.json')
            if json.loads(p.read_text()).get('vault') == slug],key=lambda j:j['submitted_at']) if root.exists() else []


def inspect(slug, job_id):
    root = job_path(job_id)
    data = json.loads((root/'job.json').read_text())
    if data['vault'] != slug:
        raise ValueError('Job belongs to another workspace')
    if data['state'] in {'submitting','queued','running','unknown'}:
        response = cli(['kernels','status',data['kernel']])
        match = re.search(r'has status "([A-Za-z_.]+)"',response)
        state = match[1].rsplit('.',1)[-1].lower() if match else 'unknown'
        if state in {'complete','completed'}: data['state'] = 'complete'
        elif state in {'error','failed','cancelled','canceled'}: data['state'] = 'failed'
        elif state in {'queued','running'}: data['state'] = state
        else: data['state'] = 'unknown'
        save(root,data)
    return data


def delete_remote(slug, job_id):
    root = job_path(job_id)
    data = json.loads((root/'job.json').read_text())
    if data['vault'] != slug:
        raise ValueError('Job belongs to another workspace')
    # Never accept a caller-supplied kernel ID: delete only this recorded job.
    cli(['kernels','delete',data['kernel'],'--yes'])
    data['state_before_delete'] = data['state']
    data.update(cleanup_pending=False,remote_deleted=True)
    if data['state'] != 'collected': data['state'] = 'deleted'
    save(root,data)
    return {**view(data),'note':'Private notebook deleted. This is not a guarantee of immediate provider backup erasure or cancellation; check the dashboard for a running session.'}


def retry(slug, job_id):
    """An explicit retry of the latest failed attempt, never a running job."""
    import curriculum
    with library.lock():
        data = inspect(slug,job_id)
        if data['state'] != 'failed' and not (data['state']=='deleted' and data.get('state_before_delete')=='failed'):
            raise ValueError('Only a confirmed failed job may be explicitly retried.')
        newer = [j for j in jobs(slug) if j['source_sha256']==data['source_sha256'] and
                 json.loads((job_path(j['id'])/'job.json').read_text())['physical_page']==data['physical_page']]
        if newer[-1]['id'] != job_id:
            raise ValueError('A newer attempt exists; inspect it instead of submitting a duplicate.')
        source = next((s for s in library.sources(slug) if s['sha256']==data['source_sha256']),None)
        if not source or library.digest(source['pdf']) != source['sha256']:
            raise ValueError('The registered original is missing or changed.')
        page = data['physical_page'];curriculum.require(slug,source['id'],page)
        import pymupdf,tempfile
        with tempfile.TemporaryDirectory() as td,pymupdf.open(source['pdf']) as document,pymupdf.open() as subset:
            subset.insert_pdf(document,from_page=page-1,to_page=page-1)
            path=Path(td)/'page.pdf';subset.save(path)
            return start(slug,path,source['sha256'],page)


def start(slug, source, source_sha256, physical_page):
    conf = study_settings.load()['kaggle']
    if not conf['enabled'] or not re.fullmatch('[a-zA-Z0-9_-]{3,50}',conf['username']):
        raise ValueError('Configure one authorized Kaggle username and enable personal study processing first.')
    seconds = conf['max_seconds']
    if type(seconds) is not int or not 300 <= seconds <= 1800:
        raise ValueError('Kaggle max_seconds must be 300–1800')
    payload = Path(source).read_bytes()
    if len(payload) > 2_000_000 or not payload.startswith(b'%PDF-'):
        raise ValueError('Kaggle accepts one PDF page up to 2 MB; use another explicit provider for larger pages.')
    import pymupdf
    with pymupdf.open(stream=payload,filetype='pdf') as document:
        if document.needs_pass or len(document) != 1:
            raise ValueError('Use one unlocked physical PDF page')
    quota = status(True)
    gpu = next((q for q in quota.get('quota') or [] if q['resource'] == 'GPU'),None)
    if not quota['authorized'] or not gpu or float(gpu['remaining'].removesuffix('h')) < seconds/3600:
        raise RuntimeError('Kaggle GPU quota is unavailable or below this job reservation. No fallback ran.')
    job_id = uuid.uuid4().hex
    root = job_path(job_id);root.mkdir(parents=True,mode=0o700)
    kernel = conf['username']+'/study-page-'+job_id
    digest = hashlib.sha256(payload).hexdigest()
    worker = Path(__file__).with_name('kaggle_worker.py').read_text()
    code = worker+'\nrun('+repr(base64.b64encode(payload).decode())+','+repr(digest)+')\n'
    library.atomic(root/'worker.py',code)
    metadata = {'id':kernel,'title':'Study page '+job_id,'code_file':'worker.py',
                'language':'python','kernel_type':'script','is_private':True,
                'enable_gpu':True,'enable_internet':True,'dataset_sources':[],
                'competition_sources':[],'kernel_sources':[],'model_sources':[]}
    library.write_json(root/'kernel-metadata.json',metadata)
    data = {'id':job_id,'vault':slug,'kernel':kernel,'source_sha256':source_sha256,
            'physical_page':physical_page,'input_sha256':digest,'state':'submitting',
            'max_seconds':seconds,'submitted_at':time.time(),'cleanup_pending':True}
    save(root,data) # Persist before upload; a lost response is never an automatic retry.
    try:
        cli(['kernels','push','-p',str(root),'--timeout',str(seconds)],timeout=60)
        data['state'] = 'queued';save(root,data)
    except RuntimeError:
        data['state'] = 'unknown';save(root,data)
        raise RuntimeError('Kaggle submission acknowledgement unavailable. Check saved job '+job_id+' before retrying.') from None
    return view(data)


def prepare(slug, source, source_sha256, physical_page, output):
    # Reuse the exact source/page job even if the locally generated subset PDF
    # has different serialization bytes on the next call.
    found = [j for j in jobs(slug) if j['source_sha256']==source_sha256 and
             json.loads((job_path(j['id'])/'job.json').read_text())['physical_page']==physical_page]
    if not found:
        return {'status':'pending','job':start(slug,source,source_sha256,physical_page)}
    job = inspect(slug,found[-1]['id']);root=job_path(job['id'])
    if job['state'] in {'failed','deleted'}:
        raise RuntimeError('The saved Kaggle job failed or was deleted. Inspect it before explicitly starting a new attempt; no automatic retry ran.')
    if job['state'] not in {'complete','collected'}:
        return {'status':'pending','job':view(job)}
    result = root/'download'
    if job['state'] != 'collected':
        result.mkdir(exist_ok=True,mode=0o700)
        cli(['kernels','output',job['kernel'],'-p',str(result),'--file-pattern','^(result.zip|receipt.json|failure.json)$','--force','--quiet'],timeout=90)
    archive = result/'result.zip';receipt_path = result/'receipt.json'
    if not archive.is_file() or archive.is_symlink() or archive.stat().st_size > 40_000_000 or not receipt_path.is_file() or receipt_path.stat().st_size>8192:
        raise RuntimeError('Kaggle returned no bounded usable result. Previous extraction is preserved.')
    receipt = json.loads(receipt_path.read_text())
    if receipt['input_sha256'] != job['input_sha256'] or receipt['output_sha256'] != library.digest(archive):
        raise ValueError('Kaggle result provenance mismatch')
    with Path(output).open('xb') as handle:handle.write(archive.read_bytes())
    Path(output).chmod(0o600)
    receipt.update(job_id=job['id'],kernel=job['kernel'],source_sha256=job['source_sha256'],physical_pdf_page=physical_page)
    job['state']='collected';save(root,job)
    if job['cleanup_pending']:
        try:delete_remote(slug,job['id'])
        except RuntimeError:pass
    receipt['cleanup_pending']=json.loads((root/'job.json').read_text())['cleanup_pending']
    return {'status':'ready','receipt':receipt}
