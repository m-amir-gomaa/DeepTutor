"""Two explicit OAuth slots; fake tokens only, no owner grants or model calls."""
import tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
from contextlib import asynccontextmanager
import httpx
import codex_pool as pool
from deeptutor.services.codex_auth import CodexAuthError
from deeptutor.services.llm.provider_core import openai_codex_provider as provider

class Service:
 def __init__(self,account):self.account=account;self.connection='connected'
 def public_status(self):return {'connection':self.connection,'model_count':1}
 def public_identity(self):return {'name':self.account,'email':None}
 async def get_token(self):return SimpleNamespace(account_id=self.account,access_token='not-a-real-token',generation=1)
 def validate_runtime_profile(self,*args):pass
 @asynccontextmanager
 async def inference_guard(self):yield

class PoolTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'pool'
  self.a=Service('fictional-primary');self.b=Service('fictional-secondary')
  self.patches=[patch.object(pool,'root',lambda:self.path),patch.object(pool,'get_codex_oauth_service',lambda:self.a),patch.object(pool,'secondary',lambda:self.b)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 async def test_quota_tries_only_the_other_account(self):
  error=provider.CodexHTTPError(429,'Allowance exhausted',{'code':'usage_limit_reached','resets_at':time.time()+120})
  invoke=AsyncMock(return_value=('answer',[],'stop'))
  result=await pool.try_other(self.a,error,await self.a.get_token(),'gpt-6.1-sol','low',invoke)
  self.assertEqual(result[0],'answer');invoke.assert_awaited_once();self.assertFalse(pool.available('primary'))
  self.assertIs(pool.preferred(self.a),self.b)
 async def test_same_account_twice_does_not_add_allowance(self):
  self.b.account=self.a.account;invoke=AsyncMock();e=provider.CodexHTTPError(429,'Exhausted')
  self.assertIsNone(await pool.try_other(self.a,e,await self.a.get_token(),'gpt-6.1-sol','low',invoke));invoke.assert_not_awaited()
  self.assertEqual(e.diagnostic['fallback_unavailable'],'same_account_signed_in_twice')
 async def test_both_unavailable_stop_after_second_rejection(self):
  e=provider.CodexHTTPError(503,'Unavailable');invoke=AsyncMock(side_effect=provider.CodexHTTPError(429,'Exhausted'))
  self.assertIsNone(await pool.try_other(self.a,e,await self.a.get_token(),'gpt-6.1-sol','low',invoke))
  invoke.assert_awaited_once();self.assertEqual(e.diagnostic['accounts_attempted'],2)
 async def test_invalid_or_forbidden_requests_never_switch(self):
  for status in [400,403,404,422]:
   invoke=AsyncMock();e=provider.CodexHTTPError(status,'Request rejected')
   self.assertIsNone(await pool.try_other(self.a,e,await self.a.get_token(),'gpt-6.1-sol','low',invoke));invoke.assert_not_awaited()
 async def test_secondary_must_support_the_exact_model(self):
  def reject(*args):raise CodexAuthError('codex_catalog_unavailable','Model absent',409)
  self.b.validate_runtime_profile=reject;e=provider.CodexHTTPError(429,'Exhausted');invoke=AsyncMock()
  self.assertIsNone(await pool.try_other(self.a,e,await self.a.get_token(),'gpt-6.1-sol','low',invoke));invoke.assert_not_awaited()
 async def test_disconnected_secondary_is_not_used(self):
  self.b.connection='disconnected';invoke=AsyncMock();e=provider.CodexHTTPError(429,'Exhausted')
  self.assertIsNone(await pool.try_other(self.a,e,await self.a.get_token(),'gpt-6.1-sol','low',invoke));invoke.assert_not_awaited()
 async def test_partial_stream_is_never_replayed(self):
  async def broken(*args,**kwargs):
   await kwargs['on_content_delta']('A real partial answer.');raise httpx.ReadError('Fixture stream interrupted')
  other=AsyncMock()
  with patch.object(pool,'preferred',lambda p:self.a),patch.object(pool,'try_other',other),patch.object(provider,'get_codex_oauth_service',lambda:self.a),patch.object(provider,'_request_codex',broken):
   response=await provider.OpenAICodexProvider().chat([{'role':'user','content':'Temporary fixture'}],model='gpt-6.1-sol')
  self.assertEqual(response.finish_reason,'error');self.assertIn('after output began',response.content)
  self.assertFalse(provider.OpenAICodexProvider._is_transient_error(response.content));other.assert_not_awaited()
 async def test_symlinked_pool_settings_are_rejected(self):
  self.path.mkdir();(self.path/'availability.json').symlink_to(Path(self.temp.name)/'elsewhere')
  with self.assertRaises(CodexAuthError):pool.state()
 async def test_manual_selection_and_strict_no_fallback(self):
  pool.select('secondary',False);self.assertIs(pool.preferred(self.a),self.b)
  invoke=AsyncMock();e=provider.CodexHTTPError(429,'Exhausted')
  self.assertIsNone(await pool.try_other(self.b,e,await self.b.get_token(),'gpt-6.1-sol','low',invoke));invoke.assert_not_awaited()
  pool.select('primary',True);self.assertIs(pool.preferred(self.a),self.a)
 async def test_selection_is_scoped_and_actual_use_is_distinct(self):
  with patch.object(pool,'current_workspace_id',lambda:'fixture-a'):
   pool.select('secondary');self.assertIs(pool.preferred(self.a),self.b)
   record=pool.record_use(self.a,'gpt-6.1-sol','fixture-session')
   self.assertEqual(record['slot'],'primary');self.assertEqual(record['selected_account'],'secondary')
   self.assertEqual(pool.public_status()['last_success']['slot'],'primary')
  with patch.object(pool,'current_workspace_id',lambda:'fixture-b'):
   self.assertEqual(pool.selection()['account'],'auto');self.assertIsNone(pool.public_status()['last_success'])
 async def test_disconnected_or_invalid_selection_preserves_settings(self):
  pool.select('primary');self.b.connection='disconnected'
  for value in ['secondary','invented']:
   with self.assertRaises(ValueError):pool.select(value)
   self.assertEqual(pool.selection()['account'],'primary')
 async def test_provider_records_fallback_account_without_token(self):
  async def response(url,headers,*args,**kwargs):
   if headers['chatgpt-account-id']==self.a.account:raise provider.CodexHTTPError(429,'Exhausted')
   return 'Fixture response',[],'stop'
  with patch.object(provider,'get_codex_oauth_service',lambda:self.a),patch.object(provider,'_request_codex',response):
   result=await provider.OpenAICodexProvider().chat([{'role':'user','content':'Temporary fixture'}],model='gpt-6.1-sol')
  self.assertEqual(result.finish_reason,'stop');self.assertEqual(result.provider_specific_fields['codex_account']['slot'],'secondary')
  self.assertNotIn('not-a-real-token',str(pool.public_status()))
 async def test_identity_allowlists_display_fields(self):
  import base64,json
  from deeptutor.services.codex_auth.service import CodexOAuthService
  payload=base64.urlsafe_b64encode(json.dumps({'name':'Fixture\nName','email':'fixture@example.invalid','access_token':'never-return-this','sub':'private-id'}).encode()).decode().rstrip('=')
  service=object.__new__(CodexOAuthService);service._store=SimpleNamespace(load_credentials=lambda:SimpleNamespace(id_token='header.'+payload+'.signature'))
  result=service.public_identity();self.assertEqual(set(result),{'name','email'});self.assertEqual(result['name'],'FixtureName')
  self.assertNotIn('never-return-this',str(result));self.assertNotIn('private-id',str(result))

if __name__=='__main__':unittest.main()
