"""Expired MCP grants refresh after restart; mock HTTP and fake tokens only."""
import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from mcp.shared.auth import OAuthToken,OAuthClientInformationFull
import httpx
from urllib.parse import parse_qs
import mcp_refresh
from deeptutor.services.mcp import oauth

class RefreshTests(unittest.IsolatedAsyncioTestCase):
 async def test_provisional_registration_does_not_corrupt_existing_grant(self):
  data={'tokens':{'access_token':'fixture-access','refresh_token':'fixture-refresh','token_type':'Bearer'},'client':{'client_id':'original-client'}}
  def write(owner,server,new):data.clear();data.update(new)
  with patch.object(oauth,'_read',lambda *args:dict(data)),patch.object(oauth,'_write',write):
   storage=oauth.OwnerTokenStorage('fixture','fixture')
   replacement=OAuthClientInformationFull(client_id='replacement-client',redirect_uris=['http://localhost/callback'])
   await storage.set_client_info(replacement)
   self.assertEqual(data['client']['client_id'],'original-client')
   self.assertEqual((await storage.get_client_info()).client_id,'replacement-client')
   await storage.set_tokens(OAuthToken(access_token='replacement-access',refresh_token='replacement-refresh',token_type='Bearer',expires_in=3600))
   self.assertEqual(data['client']['client_id'],'replacement-client')
   self.assertEqual(data['tokens']['refresh_token'],'replacement-refresh')
   self.assertGreater(data['expires_at'],time.time())
 async def exercise(self,expiry=None,broken=False,omit_refresh=False):
  fake={'tokens':{'access_token':'fixture-old','refresh_token':'fixture-refresh','token_type':'Bearer','expires_in':3600,'scope':'email profile'},
        'client':{'client_id':'fixture-client','client_secret':'fixture-secret','issuer':mcp_refresh.ISSUER,'redirect_uris':['http://localhost/callback'],'token_endpoint_auth_method':'client_secret_post'}}
  if expiry is not None:fake['expires_at']=expiry
  calls=[]
  def handle(request):
   path=request.url.path;calls.append(path)
   if path.endswith('/oauth-authorization-server/auth'):
    return httpx.Response(200,json={'issuer':mcp_refresh.ISSUER,'authorization_endpoint':mcp_refresh.ISSUER+'/authorize','token_endpoint':mcp_refresh.ISSUER+'/oauth2/token'})
   if path=='/.well-known/oauth-protected-resource/mcp/v1':
    return httpx.Response(200,json={'resource':'https://api.alphaxiv.org/mcp/v1','authorization_servers':[mcp_refresh.ISSUER]})
   if path=='/auth/oauth2/token':
    self.assertEqual(parse_qs(request.content.decode()).get('resource'),['https://api.alphaxiv.org/mcp/v1'])
    if broken:return httpx.Response(503)
    payload={'access_token':'fixture-new','token_type':'Bearer','expires_in':3600,'scope':'email profile'}
    if not omit_refresh:payload['refresh_token']='fixture-rotated'
    return httpx.Response(200,json=payload)
   self.assertEqual(path,'/mcp/v1');self.assertEqual(request.headers.get('authorization'),'Bearer '+('fixture-old' if expiry and expiry>time.time() else 'fixture-new'))
   return httpx.Response(200,json={'ok':True})
  transport=httpx.MockTransport(handle);original=httpx.AsyncClient
  async def refuse(*args):raise AssertionError('No user consent should be started')
  with tempfile.TemporaryDirectory() as td:
   def write(owner,server,data):fake.clear();fake.update(data)
   with patch.object(oauth,'_read',lambda *args:dict(fake)),patch.object(oauth,'_write',write),patch.object(oauth,'_store_path',lambda *args:Path(td)/'fixture.json'),patch.object(mcp_refresh.httpx,'AsyncClient',lambda **kwargs:original(transport=transport,**kwargs)):
    provider=mcp_refresh.RestartSafeOAuth(server_url='https://api.alphaxiv.org/mcp/v1',client_metadata=oauth.client_metadata('http://localhost/callback'),storage=oauth.OwnerTokenStorage('fixture-owner','fixture-server'),redirect_handler=refuse,callback_handler=refuse)
    if broken:
     # A transport/provider outage is not turned into a pretend valid grant.
     # The SDK may request consent after a rejected refresh; our refusing
     # handler proves that no background browser consent is launched.
     with self.assertRaises(Exception):
      async with original(transport=transport,auth=provider) as client:await client.get('https://api.alphaxiv.org/mcp/v1')
     self.assertFalse(getattr(provider,'_refresh_handles',{}))
     return
    async with original(transport=transport,auth=provider) as client:
     result=await client.get('https://api.alphaxiv.org/mcp/v1');self.assertEqual(result.status_code,200)
    self.assertFalse(getattr(provider,'_refresh_handles',{}))
    if not expiry or expiry<time.time():
     self.assertEqual(calls.count('/auth/oauth2/token'),1)
     self.assertEqual(fake['tokens']['refresh_token'],'fixture-refresh' if omit_refresh else 'fixture-rotated');self.assertGreater(fake['expires_at'],time.time())
    else:self.assertNotIn('/auth/oauth2/token',calls)
 async def test_unknown_legacy_expiry_refreshes_once_without_consent(self):await self.exercise()
 async def test_expired_absolute_clock_refreshes_without_consent(self):await self.exercise(time.time()-60)
 async def test_fresh_absolute_clock_reuses_access_token(self):await self.exercise(time.time()+3600)
 async def test_rejected_refresh_releases_lock_without_faking_a_grant(self):await self.exercise(time.time()-60,True)
 async def test_refresh_response_can_retain_the_previous_refresh_token(self):await self.exercise(time.time()-60,omit_refresh=True)

if __name__=='__main__':unittest.main()
