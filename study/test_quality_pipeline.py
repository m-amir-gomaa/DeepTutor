"""Failure-boundary tests on temporary data; never advances owner progress."""
import json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import pymupdf
import library,progress,curriculum,source_pipeline,cards,lesson_assets

class QualityPipeline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.saved=library.BASE,library.CONTROL
  library.BASE=self.root;library.CONTROL=self.root/'.control';library.CONTROL.mkdir()
  root=self.root/'test'
  for name in ['.study','references','sources','library','concepts','sessions','reviews','problems','visuals']:(root/name).mkdir(parents=True)
  library.write_json(library.CONTROL/'vaults.json',{'test':{'path':str(root),'name':'Fixture'}})
  pdf=root/'references/source.pdf'
  with pymupdf.open() as d:
   for i in range(3):d.new_page().insert_text((50,50),'Original source page '+str(i+1)+' with enough ordinary text to exercise the digital text pipeline.')
   d.save(pdf)
  self.source={'id':'source','pdf':str(pdf),'sha256':library.digest(pdf),'title':'Fixture','pdf_pages':3}
  library.write_json(root/'.study/sources.json',[self.source]);library.index('test')
  library.write_json(curriculum.path('test'),{'position':0,'units':[
   {'id':'unit-one','title':'First','sources':['source'],'ranges':[{'source':'source','first':1,'last':1}]},
   {'id':'unit-two','title':'Second','sources':['source'],'ranges':[{'source':'source','first':2,'last':3}]}]})
 def tearDown(self):library.BASE,library.CONTROL=self.saved;self.tmp.cleanup()
 def test_future_pages_locked_and_first_page_open(self):
  self.assertTrue(curriculum.allowed('test','source',1));self.assertFalse(curriculum.allowed('test','source',2))
  with self.assertRaises(ValueError):curriculum.require('test','unknown',1)
  hits=library.search('Original source page','test',page_ranges=curriculum.status('test')['allowed_ranges'])
  self.assertEqual([int(h['page']) for h in hits],[1])
 def test_initial_unit_can_only_be_planned_once_in_an_empty_route(self):
  library.write_json(curriculum.path('test'),{'position':0,'units':[{'id':'first-unit','title':'Plan introduction','sources':[],'ranges':[]}],'transitions':[]})
  planned=curriculum.first_unit('test','source',1,1,'Original introduction')
  self.assertEqual(planned['position'],0);self.assertTrue(curriculum.allowed('test','source',1));self.assertFalse(curriculum.allowed('test','source',2))
  self.assertEqual(progress.status('test')['evidence_counts'],{})
  with self.assertRaisesRegex(ValueError,'preserve it'):curriculum.first_unit('test','source',2,3,'Replacement route')
 def test_only_matching_real_evidence_can_advance_one_unit(self):
  for kind,concept in [('feedback','unit-one'),('learner_attempt','another-unit')]:
   e=progress.evidence('test',kind,concept,'Temporary test fixture, never owner data.')
   with self.assertRaises(ValueError):curriculum.advance('test',e['id'])
  self.assertEqual(curriculum.status('test')['position'],0)
  e=progress.evidence('test','self_report','unit-one','Temporary fixture explicitly states readiness.')
  self.assertEqual(curriculum.advance('test',e['id'])['position'],1)
  self.assertTrue(curriculum.allowed('test','source',2));self.assertTrue(curriculum.allowed('test','source',1))
  with self.assertRaises(ValueError):curriculum.advance('test',e['id'])
 def test_tampered_preparation_falls_back_to_original(self):
  source_pipeline.prepare('test','source',1)
  p=self.root/'test/sources/source/page-0001.md';p.write_text('Incorrect replacement')
  text,meta=source_pipeline.read_page('test',self.source,1)
  self.assertIn('Original source page',text);self.assertEqual(meta['engine'],'pymupdf')
 def test_tutor_extends_only_current_tail_with_contiguous_pages(self):
  with self.assertRaisesRegex(ValueError,'planned units remain'):curriculum.extend('test','third-unit','Third unit',[{'source':'source','first':3,'last':3}])
  route=json.loads(curriculum.path('test').read_text());route['units'][1]['ranges'][0]['last']=2;route['position']=1;library.write_json(curriculum.path('test'),route)
  for ranges in [[{'source':'source','first':1,'last':1}],[{'source':'advanced','first':1,'last':1}],[{'source':'source','first':3,'last':4}]]:
   with self.assertRaises(ValueError):curriculum.extend('test','third-unit','Third unit',ranges)
  result=curriculum.extend('test','third-unit','Third unit',[{'source':'source','first':3,'last':3}])
  self.assertEqual(result['position'],1);self.assertEqual(result['next_locked'][0]['id'],'third-unit');self.assertFalse(curriculum.allowed('test','source',3))
 def test_cached_corrected_page_is_not_overwritten(self):
  source_pipeline.prepare('test','source',1)
  root=self.root/'test/sources/source';md=root/'page-0001.md';md.write_text('Reviewed correction with a retained source locator.')
  m=root/'page-0001.json';d=json.loads(m.read_text());d['text_sha256']=library.digest(md);d['verified_against_image']=True;library.write_json(m,d)
  with patch.object(source_pipeline.subprocess,'run',side_effect=AssertionError('No unnecessary OCR')):
   result=source_pipeline.prepare('test','source',1)
  self.assertTrue(result['pages'][0]['reused_verified_bytes']);self.assertIn('Reviewed correction',md.read_text())
 def test_sparse_and_damaged_glyphs_are_visible_warnings(self):
  self.assertTrue(source_pipeline.quality(''))
  self.assertTrue(any('glyph' in w for w in source_pipeline.quality('word '*50+'\ue001')))
 def test_source_figure_retains_provenance_and_rejects_locked_or_invalid_crops(self):
  import asyncio
  import study_tools
  rows=library.records();rows['test']['workspace']={'workspace_id':'fixture','path':str(self.root/'native')}
  library.write_json(library.CONTROL/'vaults.json',rows)
  library.write_json(library.CONTROL/'native-tools.json',{})
  async def run():
   with patch.object(study_tools,'BASE',self.root):
    server=study_tools.make_server('test')
    args={'source_id':'source','pdf_page':1,'crop':[0,.02,1,.2],'label':'Original source excerpt'}
    result=await server.call_tool('source_figure',args)
    blocks=result[0] if isinstance(result,tuple) else result.content if hasattr(result,'content') else result
    data=json.loads(next(b.text for b in blocks if hasattr(b,'text')))
    self.assertEqual(data['source_sha256'],self.source['sha256'])
    self.assertIn('dt_workspace=fixture',data['image_url'])
    self.assertTrue(any(getattr(b,'type','')=='image' for b in blocks))
    self.assertEqual(progress.status('test')['evidence_counts'],{})
    for change,reason in [({'pdf_page':2},'locked'),({'crop':[-.1,0,1,1]},'inside'),({'crop':[0,float('nan'),1,1]},'finite')]:
     with self.assertRaisesRegex(Exception,reason):await server.call_tool('source_figure',{**args,**change})
    Path(self.source['pdf']).write_bytes(Path(self.source['pdf']).read_bytes()+b'\n')
    with self.assertRaisesRegex(Exception,'hash changed'):await server.call_tool('source_figure',args)
  asyncio.run(run())
 def test_modal_selection_does_not_upload_digital_or_corrected_pages(self):
  self.assertEqual(source_pipeline.backend_settings('test')['backend'],'local')
  source_pipeline.backend_settings('test','modal')
  with patch.object(source_pipeline.subprocess,'run',side_effect=AssertionError('Digital text stays local')):
   result=source_pipeline.prepare('test','source',1)
  self.assertFalse(result['cloud_upload']);self.assertEqual(result['requested_backend'],'modal')
  with patch.object(source_pipeline.subprocess,'run',side_effect=AssertionError('Verified cached bytes must stay intact')):
   result=source_pipeline.prepare('test','source',1,backend='local')
  self.assertTrue(result['pages'][0]['reused_verified_bytes'])
 def test_failed_modal_call_preserves_original_and_prior_extraction(self):
  source_pipeline.prepare('test','source',1);md=self.root/'test/sources/source/page-0001.md';original=md.read_bytes()
  from types import SimpleNamespace
  with patch.object(source_pipeline.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
   with self.assertRaisesRegex(RuntimeError,'No automatic backend fallback'):source_pipeline.prepare('test','source',1,mode='layout',backend='modal')
  self.assertEqual(md.read_bytes(),original);self.assertEqual(library.digest(self.source['pdf']),self.source['sha256'])
 def test_modal_zip_uses_same_validation_and_updates_page_index(self):
  from types import SimpleNamespace
  import hashlib
  def cloud(command,**kwargs):
   self.assertEqual(command[0],source_pipeline.MODAL_PYTHON)
   subset,result=Path(command[-2]),Path(command[-1])
   with pymupdf.open(subset) as d:self.assertEqual(d.page_count,1)
   with zipfile.ZipFile(result,'w') as z:
    z.writestr('middle_json.json',json.dumps({'pages':[{'page_idx':0}]}));z.writestr('markdown.md','Cloud fixture text with enough content to verify the page index remains consistent after processing.')
   return SimpleNamespace(returncode=0,stdout=json.dumps({'input_sha256':library.digest(subset),'output_sha256':library.digest(result),'cloud_upload':True}))
  with patch.object(source_pipeline.subprocess,'run',side_effect=cloud):result=source_pipeline.prepare('test','source',1,mode='layout',backend='modal')
  self.assertTrue(result['cloud_upload']);self.assertEqual(result['pages'][0]['engine'],'mineru-4.1.3-standard-modal-cpu')
  text,meta=source_pipeline.read_page('test',self.source,1);self.assertIn('Cloud fixture',text)
  self.assertTrue(library.search('Cloud fixture','test'))
 def test_zip_traversal_and_wrong_page_contract_rejected(self):
  out=self.root/'zip';out.mkdir()
  for bad in ['../escape.txt','/absolute.txt']:
   f=self.root/'bad.zip'
   with zipfile.ZipFile(f,'w') as z:z.writestr(bad,'x')
   with self.assertRaises(ValueError):source_pipeline.unpack_zip(f,out)
  with zipfile.ZipFile(self.root/'bad.zip','w') as z:
   z.writestr('middle_json.json',json.dumps({'pages':[{'page_idx':1}]}));z.writestr('markdown.md','text')
  with self.assertRaises(ValueError):source_pipeline.unpack_zip(self.root/'bad.zip',out)
 def test_invalid_diagram_never_invokes_native_app(self):
  with patch.object(lesson_assets.subprocess,'run',side_effect=AssertionError('Invalid graph must fail before export')):
   with self.assertRaises(ValueError):lesson_assets.drawio(self.root/'d','Fixture',[{'id':'x','label':'A'},{'id':'x','label':'B'}],[])
   with self.assertRaises(ValueError):lesson_assets.drawio(self.root/'d','Fixture',[{'id':'x','label':'A'}],[{'from':'x','to':'missing','label':'invalid'}])
 def test_card_prompt_quality_rejections_are_transactional(self):
  f={'Prompt':'What is the fixture?','Answer':'One target.','Why':'A reason.','Source':'Original fixture p.1','Track':'Fixture','Key':'quality-fixture'}
  for delta in [{'Prompt':'x'*601},{'Why':''},{'Answer':'```js\nconst x=1;\n```'},{'Answer':f['Prompt']}]:
   with self.assertRaises(ValueError):cards.queue('test',[f,{**f,**delta,'Key':'other-fixture'}])
   with cards.database('test') as d:self.assertEqual(d.execute('SELECT count(*) FROM card_outbox').fetchone()[0],0)
 def test_archived_setup_does_not_reappear_in_note_navigation(self):
  old=progress.save_note('test','concepts','Old setup','A generated fixture',concept_id='old-setup')
  with progress.db_for('test') as db:db.execute('UPDATE notes SET status="archived_setup" WHERE id="old-setup"')
  progress.save_note('test','concepts','Current unit','A generated fixture',concept_id='current-unit')
  navigation=(self.root/'test/library/GENERATED-NOTES.md').read_text()
  self.assertNotIn('Old setup',navigation);self.assertIn('Current unit',navigation)
  with self.assertRaises(ValueError):progress.save_note('test','concepts','Old setup','A generated fixture',concept_id='old-setup')

if __name__=='__main__':unittest.main()
