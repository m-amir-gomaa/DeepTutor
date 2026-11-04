"""Restart-safe alphaXiv refresh using the native MCP SDK and private storage.

Restores absolute expiry and public issuer metadata before the SDK decides
whether to refresh. Never starts consent, invents a grant or logs token values.
"""
import asyncio,fcntl,os,time
import httpx
from mcp.client.auth import OAuthClientProvider
from mcp.client.auth.utils import validate_metadata_issuer
from mcp.shared.auth import OAuthMetadata,ProtectedResourceMetadata

ISSUER='https://api.alphaxiv.org/auth'
AS_METADATA='https://api.alphaxiv.org/.well-known/oauth-authorization-server/auth'
RESOURCE_METADATA='https://api.alphaxiv.org/.well-known/oauth-protected-resource/mcp/v1'

class RestartSafeOAuth(OAuthClientProvider):
    async def _initialize(self):
        await super()._initialize()
        token=self.context.current_tokens;client=self.context.client_info
        if not token or not token.refresh_token or not client:return
        if str(getattr(client,'issuer','')).rstrip('/')!=ISSUER:
            return # Let the SDK handle an issuer change through normal consent.
        async with httpx.AsyncClient(timeout=12,follow_redirects=False) as http:
            a=await http.get(AS_METADATA);a.raise_for_status()
            r=await http.get(RESOURCE_METADATA);r.raise_for_status()
        metadata=OAuthMetadata.model_validate(a.json());validate_metadata_issuer(metadata,ISSUER)
        if str(metadata.token_endpoint)!='https://api.alphaxiv.org/auth/oauth2/token':
            raise ValueError('Unexpected alphaXiv token endpoint; refresh refused')
        resource=ProtectedResourceMetadata.model_validate(r.json())
        if str(resource.resource).rstrip('/')!='https://api.alphaxiv.org/mcp/v1':
            raise ValueError('Unexpected alphaXiv resource; refresh refused')
        self.context.oauth_metadata=metadata;self.context.auth_server_url=ISSUER
        self.context.protected_resource_metadata=resource
        expiry=await self.context.storage.get_expiry()
        # Older storage retained expires_in but no absolute clock. Refresh it
        # once rather than resetting its lifespan at every process start.
        self.context.token_expiry_time=expiry if expiry is not None else time.time()-1

    async def _refresh_token(self):
        from deeptutor.services.mcp import oauth
        storage=self.context.storage
        path=oauth._store_path(storage._owner,storage._server).with_suffix('.refresh.lock')
        handle=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            end=time.monotonic()+20
            while True:
                try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>end:raise TimeoutError('OAuth refresh is busy; retry later')
                    await asyncio.sleep(.05)
            if not hasattr(self,'_refresh_handles'):self._refresh_handles={}
            self._refresh_handles[asyncio.current_task()]=handle
            # Another process may have rotated the grant while we waited.
            self.context.current_tokens=await storage.get_tokens()
            self.context.client_info=await storage.get_client_info()
            return await super()._refresh_token()
        except BaseException:
            if getattr(self,'_refresh_handles',{}).get(asyncio.current_task())==handle:
                self._release_refresh()
            else:os.close(handle)
            raise

    def _release_refresh(self):
        handle=getattr(self,'_refresh_handles',{}).pop(asyncio.current_task(),None)
        if handle is not None:
            fcntl.flock(handle,fcntl.LOCK_UN);os.close(handle)

    async def _handle_refresh_response(self,response):
        previous=self.context.current_tokens.refresh_token if self.context.current_tokens else None
        try:
            ok=await super()._handle_refresh_response(response)
            token=self.context.current_tokens
            if ok and token and not token.refresh_token and previous:
                self.context.current_tokens=token.model_copy(update={'refresh_token':previous})
                await self.context.storage.set_tokens(self.context.current_tokens)
            return ok
        finally:self._release_refresh()

    async def _auth_flow(self,request):
        flow=super()._auth_flow(request)
        try:
            outgoing=await anext(flow)
            while True:
                response=yield outgoing
                outgoing=await flow.asend(response)
        except StopAsyncIteration:return
        finally:
            try:await flow.aclose()
            finally:self._release_refresh()
