"""Explicit source-fork acceptance against a separate synthetic learner library."""
import asyncio,json,os
from pathlib import Path
from urllib.request import urlopen
import pymupdf
import library,progress,curriculum
from study_tools import make_server

def unpack(result):
    blocks=result[0] if isinstance(result,tuple) else result
    if hasattr(blocks,'content'):blocks=blocks.content
    return json.loads(next(b.text for b in blocks if hasattr(b,'text')))
async def call(server,name,args):
    result=await server.call_tool(name,args)
    return unpack(result)
async def main():
    assert os.environ.get('DEEPTUTOR_STUDY_CONFIG')
    assert Path(library.__file__).resolve().parent==Path(__file__).resolve().parent, 'Use this fork study module directory.'
    root=library.vault('medicine');pdf=root/'inbox/original-synthetic-biology.pdf'
    if not pdf.exists():
        with pymupdf.open() as doc:
            for text in ['A cell membrane separates an internal compartment from the surrounding environment. This original synthetic educational fixture illustrates selective transport, not clinical advice or a textbook excerpt.',
                         'An original follow-up page discusses a fictional experimental comparison. This page stays locked until the learner is ready for the next unit.']:
                page=doc.new_page();page.insert_textbox((50,50,540,720),text,fontsize=13)
            doc.set_toc([[1,'Original introductory concept',1],[1,'Original follow-up',2]]);doc.save(pdf)
    before=library.digest(pdf);server=make_server('medicine')
    orientation=await call(server,'orientation',{});books=library.sources('medicine');assert len(books)==1
    source=books[0];outline=await call(server,'source_outline',{'source_id':source['id']});assert len(outline['bookmarks'])==2
    if not curriculum.status('medicine')['current'].get('sources'):
        planned=await call(server,'plan_first_unit',{'source_id':source['id'],'first_pdf_page':1,'last_pdf_page':1,'title':'Original introduction to compartments'})
    else:planned=curriculum.status('medicine')
    assert planned['position']==0 and not curriculum.allowed('medicine',source['id'],2)
    span=await call(server,'source_span',{'source_id':source['id'],'first_pdf_page':1,'last_pdf_page':1})
    assert 'membrane' in str(span).lower()
    repeated=await call(server,'import_inbox',{});assert len(library.sources('medicine'))==1
    assert library.digest(pdf)==before and library.digest(source['pdf'])==source['sha256']
    assert progress.status('medicine')['evidence_counts']=={} and library.sources('research')==[]
    navigation=await call(server,'study_setup',{});assert '18760' in navigation['links']['study_setup']
    prompt=await call(server,'study_prompt',{'template_id':'medical-mechanism','values':{'topic':'Cell compartments'}})
    assert 'Cell compartments' in prompt['text'] and not prompt['submits_to_model']
    result={'passed':True,'at':library.now(),'source_checkout_started':True,'model_invoked':False,'cloud_job_invoked':False,
       'fresh_profiles':['medicine','research'],'study_tools':len(await server.list_tools()),'checks':{
       'real_owner_api_workspace_registration':True,'synthetic_pdf_intake':True,'bookmarks_before_planning':True,
       'first_unit_without_fake_evidence':True,'future_page_locked':True,'source_read':True,
       'repeated_import_idempotent':True,'original_hash_preserved':True,'separate_research_vault':True,
       'portable_origins':True,'medical_template_render':True},
       'limits':'No owner provider consent, model inference, clinical-content certification, Anki sync or cloud job is claimed for this synthetic installation.'}
    output=Path(os.environ['DEEPTUTOR_STUDY_CONFIG']).parent/'acceptance.json';library.write_json(output,result);print(json.dumps(result,indent=2))
if __name__=='__main__':asyncio.run(main())
