"""Owner-authorized account selection using separate native OAuth services.

No credential import, copying, API-key billing or model substitution. Only
DeepTutor's own fresh OAuth grants enter the pool. Primary credentials stay put.
"""
import asyncio,json,os,time,fcntl
from pathlib import Path
import httpx
from deeptutor.services.codex_auth import get_codex_oauth_service,CodexAuthError
from deeptutor.services.codex_auth import service as auth
from deeptutor.services.codex_auth.storage import CodexCredentialStore
from deeptutor.services.codex_auth.catalog import CodexModelCatalog
from deeptutor.services.codex_auth.oauth import CodexOAuthClient
from deeptutor.services.config.model_catalog import ModelCatalogService
import library
from contextlib import contextmanager
from deeptutor.services.workspace.context import current_workspace_id

SECONDARY='secondary';TEMPORARY='temporary';_HTTP={}
def root():return auth._codex_secrets_root()/'private'/'study-codex-pool'
def check_root():
    base=root()
    if base.is_symlink() or base.parent.is_symlink():raise CodexAuthError('unsafe_storage_path','Unsafe account-pool directory.',500)
    return base
def state():
    p=check_root()/'availability.json'
    if p.is_symlink():raise CodexAuthError('unsafe_storage_path','Unsafe account-pool settings path.',500)
    return json.loads(p.read_text()) if p.exists() else {'enabled':True,'cooldowns':{}}
def save(data):
    base=check_root()
    if base.is_symlink():raise CodexAuthError('unsafe_storage_path','Unsafe account-pool directory.',500)
    base.mkdir(parents=True,exist_ok=True,mode=0o700);base.chmod(0o700)
    library.write_json(base/'availability.json',data)
@contextmanager
def locked_state():
    base=check_root();base.mkdir(parents=True,exist_ok=True,mode=0o700);base.chmod(0o700)
    path=base/'settings.lock'
    if path.is_symlink():raise CodexAuthError('unsafe_storage_path','Unsafe account-pool lock.',500)
    with path.open('a') as f:
        os.chmod(path,0o600);fcntl.flock(f,fcntl.LOCK_EX)
        try:
            data=state();yield data;save(data)
        finally:fcntl.flock(f,fcntl.LOCK_UN)
def selection():
    d=state();choices=d.get('selections',{})
    return choices.get(current_workspace_id(),choices.get('',{'account':'auto','allow_fallback':True}))
def select(account,allow_fallback=True):
    if account not in {'auto','primary','secondary','temporary'} or not isinstance(allow_fallback,bool):
        raise ValueError('Choose auto, primary, secondary or temporary and a boolean allow_fallback.')
    if account==TEMPORARY and not current_workspace_id():
        raise ValueError('Select a specific workspace before using a temporary account.')
    service=get_codex_oauth_service() if account=='primary' else secondary() if account=='secondary' else temporary() if account==TEMPORARY else None
    if service is not None and not ready(service):raise ValueError('That account is not connected. Authorize it in the account page first.')
    with locked_state() as d:
        if account==TEMPORARY:
            previous=selection()
            if previous['account']!=TEMPORARY:
                d.setdefault('before_temporary',{})[current_workspace_id()]=previous
            allow_fallback=False
        d.setdefault('selections',{})[current_workspace_id()]={'account':account,'allow_fallback':allow_fallback,'changed_at':library.now()}
    return public_status()
def record_use(service,model,session_id=None):
    info={'slot':slot(service),'identity':service.public_identity(),'model':model,'served_at':library.now(),
          'session_id':session_id,'selected_account':selection()['account']}
    with locked_state() as d:d.setdefault('last_success',{})[current_workspace_id()]=info
    return info
def secondary():
    return independent_service(SECONDARY)
def temporary():
    return independent_service(TEMPORARY)
def independent_service(name):
    # Register with the native callback router. Each owner gets an independent
    # service, OAuth state, generation-safe store and model catalog.
    pool_root=check_root();pool_root.mkdir(parents=True,exist_ok=True,mode=0o700);pool_root.chmod(0o700)
    if name not in {SECONDARY,TEMPORARY}:raise ValueError('Unknown independent account slot.')
    base=pool_root/(name+'-user');key='study-pool:'+str(base)
    if key not in auth._SERVICE_INSTANCES:
        if base.is_symlink():raise CodexAuthError('unsafe_storage_path','Unsafe account-pool directory.',500)
        base.mkdir(parents=True,exist_ok=True,mode=0o700);base.chmod(0o700)
        store=CodexCredentialStore(base);store.assert_safe_location()
        client=httpx.AsyncClient(timeout=30);_HTTP[key]=client
        auth._SERVICE_INSTANCES[key]=auth.CodexOAuthService(store,CodexModelCatalog(store,http=client),
             ModelCatalogService(base/'model-catalog.json'),oauth_client=CodexOAuthClient(client),
             callback_forward_port=auth.load_system_settings()['frontend_port'])
    return auth._SERVICE_INSTANCES[key]
def slot(service):
    if service is get_codex_oauth_service():return 'primary'
    return SECONDARY if service is secondary() else TEMPORARY
def ready(service):return service.public_status()['connection']=='connected'
def available(name):return state().get('cooldowns',{}).get(name,{}).get('until',0)<=time.time()
def preferred(primary):
    choice=selection()
    # Temporary authorizations are used only by an explicit workspace selection.
    # They never silently join the ordinary two-account fallback pool.
    if choice['account']==TEMPORARY:return temporary()
    backup=secondary();wanted=backup if choice['account']==SECONDARY else primary
    other=primary if wanted is backup else backup
    return other if choice['allow_fallback'] and state().get('enabled',True) and (not available(slot(wanted)) or not ready(wanted)) and ready(other) and available(slot(other)) else wanted
def eligible(error):
    status=getattr(error,'status_code',None)
    return status in {401,429,500,502,503,504}
def failed(service,error):
    if not eligible(error):return
    diagnostic=getattr(error,'diagnostic',{}) or {};now=time.time()
    reset=diagnostic.get('resets_at');retry=diagnostic.get('retry_after_seconds')
    delay=60
    if isinstance(reset,(int,float)) and reset>now:delay=reset-now
    elif isinstance(retry,(int,float)) and retry>0:delay=retry
    elif getattr(error,'status_code',None)==401:delay=300
    with locked_state() as d:d.setdefault('cooldowns',{})[slot(service)]={'until':now+min(delay,7*86400),'code':diagnostic.get('code','unavailable')}
def succeeded(service):
    with locked_state() as d:d.get('cooldowns',{}).pop(slot(service),None)
async def try_other(failed_service,error,failed_token,model,reasoning,invoke):
    """At most one other account, only after an HTTP rejection before streaming."""
    if slot(failed_service)==TEMPORARY:return None
    if not state().get('enabled',True) or not selection()['allow_fallback'] or not eligible(error):return None
    failed(failed_service,error)
    primary=get_codex_oauth_service();other=secondary() if failed_service is primary else primary
    if not ready(other) or not available(slot(other)):return None
    async with other.inference_guard():
        try:
            token=await other.get_token()
            if token.account_id==failed_token.account_id:
                error.diagnostic['fallback_unavailable']='same_account_signed_in_twice'
                return None
            other.validate_runtime_profile(token,model,reasoning)
            result=await invoke(token)
            succeeded(other)
            return result
        except asyncio.CancelledError:raise
        except CodexAuthError as exc:
            error.diagnostic['fallback_unavailable']=exc.code
            return None
        except Exception as exc:
            # No callback has emitted: invoke is entered only after a prior HTTP
            # rejection. Its own network/stream failures propagate, so partial
            # output is never replayed through a third or original account.
            if hasattr(exc,'status_code'):
                failed(other,exc);error.diagnostic['accounts_attempted']=2
                error.diagnostic['fallback_status']=exc.status_code
                return None
            raise
def public_status():
    d=state();rows=[]
    for name,s in [('primary',get_codex_oauth_service()),(SECONDARY,secondary()),(TEMPORARY,temporary())]:
        status=s.public_status()
        rows.append({'slot':name,'identity':s.public_identity(),'connection':status['connection'],'model_count':max(status['model_count'],len(status.get('models',[]))),
                     'operation_state':status.get('operation_state'),'error_code':status.get('error_code'),
                     'cooldown_until':d.get('cooldowns',{}).get(name,{}).get('until')})
    return {'enabled':d.get('enabled',True),'selection':selection(),'selection_scope':'this workspace' if current_workspace_id() else 'owner default',
            'effective_next_slot':slot(preferred(get_codex_oauth_service())),
            'last_success':d.get('last_success',{}).get(current_workspace_id()),
            'accounts':rows,'same_model':True,'separate_api_billing':False,'temporary_explicit_only':True}

async def checked_public_status():
    d=public_status();d['distinct_accounts']=None
    if all(a['connection']=='connected' for a in d['accounts'][:2]):
        try:
            a=await get_codex_oauth_service().get_token();b=await secondary().get_token()
            d['distinct_accounts']=a.account_id!=b.account_id
        except CodexAuthError:pass
    return d

async def disconnect_temporary():
    # Native logout refuses active inference and clears/revokes only this grant.
    await temporary().logout()
    with locked_state() as d:
        previous=d.get('before_temporary',{})
        for workspace,choice in d.get('selections',{}).items():
            if choice.get('account')==TEMPORARY:
                d['selections'][workspace]=previous.get(workspace,{'account':'auto','allow_fallback':True})
        d.pop('before_temporary',None)
        d.get('cooldowns',{}).pop(TEMPORARY,None)
    return public_status()

PAGE=Path(__file__).with_name('codex_accounts.html').read_text()
