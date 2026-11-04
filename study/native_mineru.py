"""Explicit compatibility CLI: DeepTutor's -p/-o contract → local MinerU 4 ZIP.

Only bounded PDF parts (1–8 pages). No remote route, credential or model download.
The ordinary study service processes source physical pages directly instead.
"""
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path
import pymupdf
from source_pipeline import WRAPPER,unpack_zip
import study_settings

INSTALL=Path(__file__).resolve().parent
MODELS=Path(study_settings.load().get('mineru_models',Path.home()/'.mineru/models'))
REQUIRED=['MinerU2.5-Pro-2605-1.2B-GGUF/MinerU2.5-Pro-2605-1.2B-Q8_0.gguf',
          'MinerU2.5-Pro-2605-1.2B-GGUF/mmproj-MinerU2.5-Pro-2605-1.2B-Q8_0.gguf',
          'MinerU-4_models_onnx/Layout/PP-DocLayoutV2/inference.onnx']
def ready():return Path(WRAPPER).is_file() and all((MODELS/p).is_file() and (MODELS/p).stat().st_size>1_000_000 for p in REQUIRED)
def convert(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    if source.suffix.lower()!='.pdf':raise ValueError('This pinned study adapter accepts PDF parts only')
    if not ready():raise RuntimeError('Pinned offline MinerU model files are missing; no download attempted')
    with pymupdf.open(source) as doc:
        if not 1<=len(doc)<=8:raise ValueError('Use a 1–8 page PDF part, or the study prepare_pdf tool with original physical page numbers')
        folder=output/source.stem
        if folder.exists():raise ValueError('Native attempt output exists; preserve it and use a fresh attempt')
        folder.mkdir(parents=True);blocks=[];sections=[]
        for i,page in enumerate(doc):
            print(f'Local MinerU page {i+1}/{len(doc)}',flush=True)
            with tempfile.TemporaryDirectory(prefix='.mineru4-',dir=folder) as tmp:
                tmp=Path(tmp);one=tmp/'page.pdf'
                with pymupdf.open() as subset:subset.insert_pdf(doc,from_page=i,to_page=i);subset.save(one)
                archive=tmp/'result.zip'
                run=subprocess.run(['bash',WRAPPER,str(one),'--tier','standard','--ocr-mode','auto','--format','zip','-o',str(archive)],timeout=180)
                if run.returncode:raise RuntimeError('Local MinerU failed; native attempt remains incomplete')
                parsed=tmp/'parsed';parsed.mkdir();text,middle=unpack_zip(archive,parsed)
                target=folder/f'page-{i+1:04d}';parsed.rename(target)
                # The raw per-page IR and assets remain together. Combined Markdown
                # links point to that actual page directory after native promotion.
                text=re.sub(r'(?<=\()images/',f'{target.name}/images/',text)
                text=re.sub(r'(?<=src=")images/',f'{target.name}/images/',text)
                sections.append(f'## Physical PDF page {i+1}\n\n'+text)
                blocks.append({'type':'text','text':text,'page_idx':i})
        (folder/(source.stem+'.md')).write_text('\n\n'.join(sections))
        (folder/(source.stem+'_content_list.json')).write_text(json.dumps(blocks,ensure_ascii=False))
        (folder/'study-parser-provenance.json').write_text(json.dumps({'engine':'MinerU 4.1.3 Standard local','pages':len(doc),'indices':list(range(len(doc))),'original_pdf_preserved':True,'cloud_upload':False,'warning':'Raw OCR; verify symbols, tables and phonetics against the original PDF.'},indent=2))
    return folder
def main():
    p=argparse.ArgumentParser();p.add_argument('--version',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('-p','--path');p.add_argument('-o','--output');a=p.parse_args()
    if a.version:print('study-mineru compatibility 1 / MinerU 4.1.3 local');return
    if a.check:print(json.dumps({'ready':ready(),'offline':True}));raise SystemExit(0 if ready() else 1)
    if not a.path or not a.output:p.error('PDF source -p and output directory -o are required')
    print(convert(a.path,a.output))
if __name__=='__main__':main()
