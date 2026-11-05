"""Shared prompts, discipline profiles and non-secret owner setup information."""
import json,re,shlex,subprocess
from pathlib import Path
import study_settings

ROOT=Path(__file__).resolve().parent
def profiles():return json.loads((ROOT/'discipline_profiles.json').read_text())
def prompts():return json.loads((ROOT/'prompt_catalog.json').read_text())
def render(template_id,values=None):
    row=next((p for p in prompts() if p['id']==template_id),None)
    if row is None:raise ValueError('Unknown prompt template.')
    values=values or {}
    needed=set(re.findall(r'\{\{([a-z_]+)\}\}',row['text']))
    if set(values)!=needed:raise ValueError('Provide exactly these fields: '+', '.join(sorted(needed)))
    if any(not isinstance(v,str) or not v.strip() or len(v)>3000 for v in values.values()):raise ValueError('Each prompt field needs 1–3000 characters.')
    text=re.sub(r'\{\{([a-z_]+)\}\}',lambda m:values[m[1]].strip(),row['text'])
    return {'id':row['id'],'title':row['title'],'text':text,'submits_to_model':False,'changes_settings':False}
def links(workspace_id=''):
    from urllib.parse import urlencode
    query='?'+urlencode({'dt_workspace':workspace_id}) if workspace_id else ''
    api=study_settings.origin('frontend')+'/api/settings'
    return {'study_setup':api+'/study/page'+query,'codex_accounts':api+'/providers/openai-codex/pool/page'+query,
            'chat':study_settings.origin('frontend')+'/chat'+query,
            'modal_dashboard':'https://modal.com/settings','modal_token_docs':'https://modal.com/docs/cli/latest/token',
            'modal_profile_docs':'https://modal.com/docs/cli/latest/profile'}
def modal_status(check=False):
    conf=study_settings.load()['modal'];python=conf['python']
    command=[python,str(ROOT/'modal_status.py')]+(['--check'] if check else [])
    try:
        r=subprocess.run(command,capture_output=True,text=True,timeout=20)
        detail=json.loads(r.stdout) if r.returncode==0 else {'sdk_available':False,'error':'Modal status unavailable; check the isolated client installation.'}
    except (OSError,subprocess.TimeoutExpired,ValueError):detail={'sdk_available':False,'error':'Modal status unavailable; use the owner terminal instructions.'}
    return {**detail,'cloud_enabled':conf['enabled'],'app':conf['app'],'profile_override':conf['profile'] or None,
            'monthly_reservation_limit_usd':conf['reservation_limit_usd'],'reserve_usd':conf['reserve_usd'],
            'credentials_returned':False,'instructions':{
              'login':shlex.join([python,'-m','modal','token','new']),
              'replace_token':shlex.join([python,'-m','modal','token','set','--token-id','-','--token-secret','-']),
              'profiles':shlex.join([python,'-m','modal','profile','list']),
              'current_profile':shlex.join([python,'-m','modal','profile','current'])}}
def data(workspace_id=''):
    return {'code_location':str(ROOT),'profiles':profiles(),'prompts':prompts(),'links':links(workspace_id),
            'meaning':'Copying a template does not execute it, change settings, unlock material or record learning.'}
def guide(kind):
    names={'human':'SETUP-HUMAN.md','agent':'SETUP-AGENT.md'}
    if kind not in names:raise ValueError('Choose the human or agent guide.')
    return (ROOT/names[kind]).read_text()
def human_help(topic,workspace_id=''):
    route=links(workspace_id)
    topics={
      'overview':'Choose the workspace, then use Start or resume a unit. The agent reads the current sources and checkpoint, teaches, prepares useful notes/visuals/cards and leaves a brief check. Ask for setup instructions only when needed.',
      'accounts':'Open the account-control link. Read selected, effective-next and latest-completed accounts separately. Authorize each account yourself if requested. Switching affects subsequent model calls and keeps each account limit. If no model can answer, this page still works.',
      'books':'Put your owned PDF in this subject inbox and ask the agent to import it. It verifies a managed copy and indexes physical pages. Choose the actual introductory unit together. Importing a source does not mean you have learned it or that every page passed OCR review.',
      'cards':'The agent queues and synchronizes focused cards after an explanation. Open the selected Study::NAME deck in Anki and review it yourself. If delivery is pending, the setup agent must connect the local authenticated Anki service and configure its note type; it must not rate your cards.',
      'memory':'Tell the agent a durable preference explicitly, such as language, useful visual style or check frequency, and ask it to save and read it back. Notes and chronological checkpoints are separate from native profile/preferences. Never save credentials or identifiable medical records in memory.',
      'visuals':'Use relevant original book figures first. The agent can create original plots, simulations, mechanism diagrams or animations when they reveal structure or reasoning beyond the page. Require faithful labels/units, source comparison, calculation checks and inspection of the actual render or interaction; decorative text slides are insufficient for a mechanism. Missing renderers need setup; successful file creation alone is not content verification.',
      'first_setup':'Give your setup assistant SETUP-AGENT.md from the fork. It should ask only for missing goals, sources, language and provider choices, do the technical setup, and pause only for your sign-in or another necessary owner action. You do not need to read the entire manual first.',
      'modal':'Use the Modal section of Study setup. Run its displayed browser-login command in your own terminal, or use hidden token prompts for a dashboard-issued token. After renewal, check the private worker. Selecting a new Modal workspace can require deployment there. No token belongs in chat; no cloud job or budget change is needed just to inspect setup.'}
    if topic not in topics:raise ValueError('Choose one of: '+', '.join(topics))
    result={'topic':topic,'human_steps':topics[topic],'links':route,
            'agent_instruction':'Do routine technical work yourself. Explain only the immediate owner action and why it is needed. Do not send the learner through the whole manual or claim untested readiness.'}
    if topic=='modal':
        python=study_settings.load()['modal']['python']
        result['owner_terminal_commands']={'browser_login':shlex.join([python,'-m','modal','token','new']),
          'hidden_token_prompts':shlex.join([python,'-m','modal','token','set','--token-id','-','--token-secret','-'])}
    return result
PAGE=(ROOT/'setup_center.html').read_text() if (ROOT/'setup_center.html').exists() else ''

def install_routes(router,require_owner):
    """Install only owner-facing routes; no token input/storage endpoint exists."""
    import asyncio
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse
    from deeptutor.services.workspace.context import workspace_context
    @router.get('/study/page')
    async def study_setup_page(dt_workspace: str | None = None):
        require_owner()
        with workspace_context(dt_workspace):pass
        return HTMLResponse(PAGE,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'})
    @router.get('/study/data')
    async def study_setup_data(dt_workspace: str | None = None):
        require_owner()
        with workspace_context(dt_workspace) as scope:return data(scope.workspace_id)
    @router.post('/study/render')
    async def study_prompt_render(body: dict):
        require_owner()
        try:
            if set(body)!={'template_id','values'} or not isinstance(body['values'],dict):raise ValueError('Provide template_id and values.')
            return render(body['template_id'],body['values'])
        except (ValueError,TypeError) as exc:raise HTTPException(status_code=422,detail=str(exc)) from None
    @router.get('/study/guide/{kind}')
    async def study_setup_guide(kind: str):
        require_owner()
        try:return {'content':guide(kind)}
        except ValueError as exc:raise HTTPException(status_code=404,detail=str(exc)) from None
    @router.get('/study/modal')
    async def study_modal_status():
        require_owner()
        return await asyncio.to_thread(modal_status)
    @router.post('/study/modal/check')
    async def study_modal_check():
        require_owner()
        return await asyncio.to_thread(modal_status,True)
