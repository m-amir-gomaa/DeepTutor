"""Portable prompt/profile/configuration and owner-route boundaries; no credentials."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI,APIRouter,HTTPException
from fastapi.testclient import TestClient
import setup_center,study_settings

class SetupCenter(unittest.TestCase):
 def test_all_prompts_render_and_ids_are_unique(self):
  import re
  rows=setup_center.prompts();self.assertEqual(len({r['id'] for r in rows}),len(rows))
  for row in rows:
   fields=set(re.findall(r'\{\{([a-z_]+)\}\}',row['text']))
   result=setup_center.render(row['id'],{k:'Original synthetic learning topic' for k in fields})
   self.assertNotIn('{{',result['text']);self.assertFalse(result['changes_settings']);self.assertFalse(result['submits_to_model'])
 def test_prompt_values_are_required_and_literal(self):
  for template,values in [('missing',{}),('repair',{}),('repair',{'topic':''}),('repair',{'topic':'x','unexpected':'y'}),('repair',{'topic':'x'*3001})]:
   with self.assertRaises(ValueError):setup_center.render(template,values)
  result=setup_center.render('repair',{'topic':'<script>window.fixture=1</script>'})
  self.assertIn('<script>',result['text']) # Data remains data; UI uses textContent/value.
 def test_disciplines_have_common_workflow_and_medical_evidence_preferences(self):
  for name,profile in setup_center.profiles().items():
   self.assertTrue({'study-session','study-visuals','study-apps'}<=set(profile['skills']))
  self.assertIn('pubmed',setup_center.profiles()['medicine']['research_services'])
  self.assertIn('preprints',setup_center.profiles()['research']['teaching'])
 def test_portable_config_defaults_do_not_assume_cloud_credit(self):
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'DEEPTUTOR_STUDY_CONFIG':td+'/missing.json'}),patch.object(study_settings.Path,'home',return_value=Path(td)),patch.object(study_settings.sys,'executable','/usr/bin/python3'):
   conf=study_settings.load();self.assertFalse(conf['modal']['enabled']);self.assertEqual(conf['modal']['credit_ceiling_usd'],0)
   self.assertEqual(conf['library_root'],str(Path(td)/'DeepTutorStudy'));self.assertEqual(conf['python'],'/usr/bin/python3')
 def test_fresh_medical_setup_is_idempotent_and_preserves_edits(self):
  import manage
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'DEEPTUTOR_STUDY_CONFIG':td+'/installation.json'}):
   first=manage.initialize('medicine','Medical study','medicine',td+'/library');self.assertEqual(first['status'],'prepared')
   learner=Path(first['path'])/'LEARNER.md';learner.write_text('Owner preferences must remain.')
   again=manage.initialize('research','Renamed by a test','medicine');self.assertEqual(again['status'],'already prepared')
   self.assertEqual(learner.read_text(),'Owner preferences must remain.')
   state=json.loads((Path(first['path'])/'.study/curriculum.json').read_text())
   self.assertEqual(state['position'],0);self.assertEqual(state['units'][0]['sources'],[])
   with self.assertRaises(ValueError):manage.initialize('medicine','Other','other',td+'/different-library')
 def test_attach_preserves_existing_workspace_identity_when_vault_paths_differ(self):
  import manage
  record={'path':'/tmp/obsidian-fixture','workspace':{'workspace':{'workspace_id':'original-workspace','path':'/tmp/private-content-fixture'}}}
  original={'workspace_id':'original-workspace','path':'/tmp/private-content-fixture'}
  misleading={'workspace_id':'wrong-new-workspace','path':'/tmp/obsidian-fixture'}
  self.assertIs(manage.existing_workspace(record,[misleading,original]),original)
  with self.assertRaisesRegex(ValueError,'preserve the mapping'):manage.existing_workspace(record,[misleading])
 def test_config_rejects_secrets_and_credential_urls(self):
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'DEEPTUTOR_STUDY_CONFIG':td+'/config.json'}):
   p=Path(td)/'config.json'
   for data in [{'modal':{'token_secret':'fixture'}},{'frontend_url':'http://user:password@localhost'},{'token':'fixture'}]:
    p.write_text(json.dumps(data))
    with self.assertRaises(ValueError):study_settings.load()
 def test_guides_are_bounded_known_files(self):
  self.assertIn('Fresh installation',setup_center.guide('human'))
  self.assertIn('Agent setup contract',setup_center.guide('agent'))
  with self.assertRaises(ValueError):setup_center.guide('../../private')
 def test_links_preserve_workspace_and_ports(self):
  links=setup_center.links('fixture workspace');self.assertIn('dt_workspace=fixture+workspace',links['study_setup'])
  self.assertTrue(links['codex_accounts'].startswith(study_settings.origin('frontend')))
 def test_just_in_time_human_help_is_specific_and_never_requests_chat_tokens(self):
  help=setup_center.human_help('modal','fixture')
  self.assertIn('hidden_token_prompts',help['owner_terminal_commands'])
  self.assertIn('--token-secret -',help['owner_terminal_commands']['hidden_token_prompts'])
  self.assertIn('No token belongs in chat',help['human_steps'])
  self.assertIn('immediate owner action',help['agent_instruction'])
  with self.assertRaises(ValueError):setup_center.human_help('../../private')
 def test_routes_require_owner_and_reject_malformed_render(self):
  app=FastAPI();router=APIRouter(prefix='/api/settings');owner={'allowed':False}
  def require():
   if not owner['allowed']:raise HTTPException(status_code=403)
  setup_center.install_routes(router,require);app.include_router(router);client=TestClient(app)
  for method,path,kwargs in [('GET','/guide/human',{}),('GET','/modal',{}),('POST','/render',{'json':{'template_id':'start','values':{}}})]:
   self.assertEqual(client.request(method,'/api/settings/study'+path,**kwargs).status_code,403)
  owner['allowed']=True
  self.assertEqual(client.post('/api/settings/study/render',json={'template_id':'repair','values':{}}).status_code,422)
  self.assertEqual(client.post('/api/settings/study/render',json={'template_id':'start','values':{}}).status_code,200)
  self.assertEqual(client.get('/api/settings/study/guide/human').status_code,200)

if __name__=='__main__':unittest.main()
