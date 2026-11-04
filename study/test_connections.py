"""OAuth lifecycle, resource capacity and safe account-limit errors; no real grants."""
import asyncio,json,unittest
from unittest.mock import patch,AsyncMock,Mock
from urllib.parse import urlparse,parse_qs
from deeptutor.services.mcp import oauth,user_config
from deeptutor.services.llm.provider_core.openai_codex_provider import _describe_error,OpenAICodexProvider

class CodexErrors(unittest.TestCase):
 def test_account_allowance_shows_reset_without_retry(self):
  message,diagnostic=_describe_error(429,json.dumps({'error':{'type':'usage_limit_reached','resets_at':1793908800,'private_value':'not-for-output'}}).encode(),{})
  self.assertIn('Resets at',message);self.assertNotIn('private_value',message);self.assertNotIn('not-for-output',str(diagnostic))
  self.assertFalse(OpenAICodexProvider._is_transient_error('Error calling Codex: '+message))
 def test_throttling_retains_wait_time(self):
  message,data=_describe_error(429,b'{"error":{"code":"slow_down"}}',{'retry-after':'60'})
  self.assertIn('60 seconds',message);self.assertEqual(data['retry_after_seconds'],60)
  self.assertFalse(OpenAICodexProvider._is_transient_error(message))
 def test_unknown_payload_does_not_leak_text(self):
  message,data=_describe_error(500,b'<html>private upstream token</html>',{})
  self.assertNotIn('private',message);self.assertEqual(data['code'],'unknown')
  self.assertTrue(OpenAICodexProvider._is_transient_error('network timeout'))
 def test_configurable_capacity_stays_bounded(self):
  for value,expected in [('12',12),('1000',32),('1',8),('broken',8)]:
   with patch.dict('os.environ',{'DEEPTUTOR_MCP_MAX_SERVERS':value}):self.assertEqual(user_config._server_capacity(),expected)
 def test_native_libraries_do_not_forward_provider_environment(self):
  from deeptutor.services.sandbox.backends import RestrictedSubprocessBackend
  with patch.dict('os.environ',{'PRIVATE_ACCEPTANCE_PROVIDER_KEY':'fixture-not-a-real-key'}):
   env=RestrictedSubprocessBackend()._build_env({'LD_LIBRARY_PATH':'/tmp/fixture-native-library'})
  self.assertEqual(env['LD_LIBRARY_PATH'],'/tmp/fixture-native-library')
  self.assertNotIn('PRIVATE_ACCEPTANCE_PROVIDER_KEY',env)

class OAuthLifecycle(unittest.IsolatedAsyncioTestCase):
 async def asyncTearDown(self):
  for flow in list(oauth._PENDING.values()):
   if flow.task:flow.task.cancel()
  oauth._PENDING.clear();await asyncio.sleep(0)
 async def exercise(self,fail=False):
  callbacks={};authorized=False;manager=Mock();manager.reconnect_server=AsyncMock()
  def auth(**kwargs):callbacks.update(kwargs);return None
  class Client:
   def __init__(self,**kwargs):pass
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   async def post(self,*args,**kwargs):
    nonlocal authorized
    await callbacks['redirect_handler']('https://provider.example/authorize?state=fixture-state')
    code,state=await callbacks['callback_handler']()
    if fail:raise RuntimeError('Temporary test token exchange failure')
    self.assert_valid=(code=='fixture-code' and state=='fixture-state');authorized=True
  with patch.object(oauth,'forget'),patch.object(oauth,'build_auth',auth),patch.object(oauth,'oauth_state',lambda *args:oauth.OAuthState(authorized=authorized)),patch('httpx.AsyncClient',Client),patch('deeptutor.services.mcp.get_mcp_manager',lambda:manager):
   url=await oauth.begin_authorization(server_url='https://provider.example/mcp',server_name='fixture',owner_id='test-owner',redirect_uri='http://localhost/callback')
   self.assertEqual(parse_qs(urlparse(url).query)['state'],['fixture-state'])
   ok,message=await oauth.finish_authorization('fixture-state','fixture-code')
   if fail:self.assertFalse(ok);self.assertIn('failed',message);manager.reconnect_server.assert_not_awaited()
   else:self.assertTrue(ok);manager.reconnect_server.assert_awaited_once_with('test-owner','fixture')
   self.assertFalse(oauth.complete_authorization('fixture-state','replayed-code'))
 async def test_grant_exchange_precedes_success_and_reconnect(self):await self.exercise()
 async def test_failed_exchange_is_not_success(self):await self.exercise(fail=True)
 async def test_unknown_callback_rejected(self):self.assertFalse((await oauth.finish_authorization('missing','code'))[0])

if __name__=='__main__':unittest.main()
