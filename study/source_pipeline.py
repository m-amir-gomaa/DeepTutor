"""Bounded local PDF preparation, real MinerU 4 ZIP contract and page provenance.

The tutor receives warnings, not an invented 'perfect OCR' label. Original PDFs
are immutable. Slow/failed extraction never replaces a previously usable page.
"""
import hashlib,json,re,subprocess,tempfile,zipfile
from pathlib import Path,PurePosixPath
import pymupdf
import library
import study_settings

WRAPPER=study_settings.tool('mineru-local',str(Path(__file__).parent/'bin/mineru-local'))
MODAL_PYTHON=study_settings.load()['modal']['python']
def backend_settings(slug,backend=None):
    path=library.vault(slug)/'.study/pdf-processing.json'
    if backend is not None:
        if backend not in {'local','modal'}:raise ValueError('Choose local or modal')
        library.write_json(path,{'backend':backend,'changed_at':library.now()})
    selected=json.loads(path.read_text()) if path.exists() else {'backend':'local'}
    qualification=library.CONTROL/'modal-qualification.json'
    if not qualification.exists():qualification=library.CONTROL/'20261104/agent-controls/modal-pipeline.json'
    checked=json.loads(qualification.read_text()) if qualification.exists() else None
    return {**selected,'local_default':True,'modal_client_installed':Path(MODAL_PYTHON).is_file(),
            'last_modal_qualification':None if not checked else {'passed':checked.get('passed'),'at':checked.get('at')},
            'modal_scope':'private personal CPU worker; one-page subsets only; no public endpoint',
            'monthly_modal_reservation_limit_usd':study_settings.load()['modal']['reservation_limit_usd'],
            'per_job_reservation_usd':study_settings.load()['modal']['reserve_usd'],
            'policy':'Usable digital text and verified cached pages stay local. Modal is used only for OCR/layout when explicitly selected; no automatic cloud fallback. A reservation is not an exact bill.'}
def quality(text):
    warnings=[]
    if len(re.findall(r'\w',text))<40:warnings.append('Sparse or missing text layer: inspect the page image; OCR may be needed.')
    if '\ufffd' in text or any(0xE000<=ord(c)<=0xF8FF for c in text):warnings.append('Replacement/private-use glyphs: verify mathematical symbols or phonetics against the image.')
    return warnings
def read_page(slug,source,page):
    root=library.vault(slug)/'sources'/source['id'];md=root/f'page-{page:04d}.md';meta=root/f'page-{page:04d}.json'
    if md.exists() and meta.exists():
        d=json.loads(meta.read_text())
        if d.get('source_sha256')==source['sha256'] and d.get('text_sha256')==library.digest(md):
            return md.read_text(),d
    with pymupdf.open(source['pdf']) as pdf:text=pdf[page-1].get_text()
    # Earlier prepared pages have no verified provenance; do not silently trust them.
    return text,{'engine':'pymupdf','physical_pdf_page':page,'source_sha256':source['sha256'],'warnings':quality(text),'verified_against_image':False}
def unpack_zip(archive,destination):
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist())>150_000_000:raise ValueError('Parser archive too large')
        for i in z.infolist():
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or (i.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Unsafe parser archive path')
        z.extractall(destination)
    middle=list(destination.rglob('middle_json.json'))
    if len(middle)!=1:raise ValueError('Expected one MinerU 4 middle_json.json')
    d=json.loads(middle[0].read_text())
    if len(d.get('pages',[]))!=1 or d['pages'][0].get('page_idx')!=0:raise ValueError('Expected exactly one local subset page')
    markdown=middle[0].parent/'markdown.md'
    if not markdown.is_file() or not markdown.read_text().strip():raise ValueError('Parser returned no usable Markdown')
    return markdown.read_text(),d
def prepare(slug,source_id,first,last=None,mode='auto',backend=None):
    backend=backend_settings(slug)['backend'] if backend is None else backend
    if backend not in {'local','modal'}:raise ValueError('Choose local or modal')
    s=next((s for s in library.sources(slug) if s['id']==source_id),None)
    if not s:raise ValueError('Unknown registered source')
    last=first if last is None else last
    if not 1<=first<=last<=s['pdf_pages'] or last-first>=8:raise ValueError('Prepare one to eight physical PDF pages')
    if mode not in {'auto','layout'}:raise ValueError('Use auto or layout')
    if mode=='layout' and first!=last:raise ValueError('Prepare one layout/OCR page per call; digital text spans may contain eight pages')
    root=library.vault(slug)/'sources'/source_id;root.mkdir(parents=True,exist_ok=True,mode=0o700)
    receipts=[];uploaded=False
    with library.lock(),pymupdf.open(s['pdf']) as pdf:
        if library.digest(s['pdf'])!=s['sha256']:raise ValueError('Registered source hash changed')
        sparse=sum(any('Sparse' in w for w in quality(pdf[p-1].get_text())) for p in range(first,last+1))
        if sparse>1:raise ValueError('Prepare scanned pages one at a time to keep the local tool deadline bounded')
        for page in range(first,last+1):
            current_md=root/f'page-{page:04d}.md';current_meta=root/f'page-{page:04d}.json'
            if current_md.exists() and current_meta.exists():
                saved=json.loads(current_meta.read_text())
                if saved.get('source_sha256')==s['sha256'] and saved.get('text_sha256')==library.digest(current_md) and (mode=='auto' or saved.get('engine','').startswith('mineru')):
                    receipts.append({**saved,'reused_verified_bytes':True});continue
            text=pdf[page-1].get_text();warnings=quality(text);engine='pymupdf';assets=None;cloud_receipt=None
            # A chapter is bounded to eight pages; OCR pages run sequentially on this laptop.
            if mode=='layout' or any('Sparse' in w for w in warnings):
                with tempfile.TemporaryDirectory(prefix='.parse-',dir=root) as td:
                    td=Path(td);subset=td/'page.pdf';result=td/'result.zip'
                    with pymupdf.open() as one:
                        one.insert_pdf(pdf,from_page=page-1,to_page=page-1);one.save(subset)
                    if backend=='local':
                        command=['bash',WRAPPER,str(subset),'--tier','standard','--ocr-mode','auto','--format','zip','-o',str(result)]
                    else:
                        command=[MODAL_PYTHON,str(Path(__file__).with_name('modal_mineru_client.py')),str(subset),str(result)]
                    run=subprocess.run(command,capture_output=True,text=True,timeout=180 if backend=='local' else 360)
                    if run.returncode or not result.exists():raise RuntimeError(backend.title()+' MinerU failed; original and previous extraction preserved. No automatic backend fallback was attempted.')
                    if backend=='modal':
                        cloud_receipt=json.loads(run.stdout)
                        if cloud_receipt['input_sha256']!=library.digest(subset) or cloud_receipt['output_sha256']!=library.digest(result):raise ValueError('Cloud parser provenance mismatch')
                        uploaded=True
                    parsed=td/'unpacked';parsed.mkdir();text,middle=unpack_zip(result,parsed)
                    engine='mineru-4.1.3-standard-local' if backend=='local' else 'mineru-4.1.3-standard-modal-cpu';assets=root/f'page-{page:04d}-assets'
                    if assets.exists():
                        # Preserve older assets too; source hash keys are stable, reprocessing is uncommon.
                        assets=root/(f'page-{page:04d}-assets-'+hashlib.sha256(result.read_bytes()).hexdigest()[:10])
                    parsed.rename(assets)
                    warnings=quality(text)+['OCR output requires image verification for formulas, IPA and table structure.']
            meta={'source_id':source_id,'source_sha256':s['sha256'],'physical_pdf_page':page,'engine':engine,
                  'warnings':warnings,'verified_against_image':False,'prepared_at':library.now(),
                  'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'assets':str(assets) if assets else None}
            if cloud_receipt:meta['cloud_receipt']=cloud_receipt
            library.atomic(root/f'page-{page:04d}.md',text);library.write_json(root/f'page-{page:04d}.json',meta)
            # Update the physical-page FTS row even when original PDF bytes did not change.
            with library.connection() as db:
                db.execute('DELETE FROM pages WHERE vault=? AND source_id=? AND page=?',(slug,source_id,page))
                db.execute('INSERT INTO pages VALUES(?,?,?,?)',(slug,source_id,page,text))
            receipts.append(meta)
    return {'pages':receipts,'requested_backend':backend,'cloud_upload':uploaded,'meaning':'Extraction is source preparation, not learning or a fidelity guarantee. Cached verified bytes are preserved across backend choices.'}
