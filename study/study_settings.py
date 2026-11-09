"""Portable, non-secret study configuration; credentials stay in native stores."""
import json,os,shutil,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def config_path():
    return Path(os.environ.get('DEEPTUTOR_STUDY_CONFIG',ROOT/'installation.json')).expanduser()
def load():
    p=config_path();raw=json.loads(p.read_text()) if p.exists() else {}
    if not isinstance(raw,dict):raise ValueError('Study configuration must be an object.')
    forbidden={'token','token_id','token_secret','api_key','password','access_token','refresh_token'}
    def check(value):
        if isinstance(value,dict):
            if forbidden.intersection(value):raise ValueError('Use native credential storage, not study configuration.')
            for v in value.values():check(v)
        elif isinstance(value,list):
            for v in value:check(v)
    check(raw)
    base=Path(raw.get('library_root',Path.home()/'DeepTutorStudy')).expanduser().resolve()
    defaults={'library_root':str(base),'backend_url':'http://127.0.0.1:8001','frontend_url':'http://127.0.0.1:3782',
      'python':sys.executable,'native_library_path':'','startup_catalogue_root':str(base/'catalogues'),
      'tools':{},'kaggle':{'enabled':False,'username':'','max_seconds':1800},'modal':{'python':sys.executable,'app':'deeptutor-study-mineru','profile':'',
                        'enabled':False,'reservation_limit_usd':5,'credit_ceiling_usd':0,'reserve_usd':.25}}
    defaults.update({k:v for k,v in raw.items() if k not in {'modal','tools','kaggle'}})
    defaults['kaggle'].update(raw.get('kaggle',{}))
    defaults['modal'].update(raw.get('modal',{}));defaults['tools'].update(raw.get('tools',{}))
    for key in ['backend_url','frontend_url']:
        from urllib.parse import urlsplit
        parts=urlsplit(defaults[key])
        if parts.scheme not in {'http','https'} or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError('Use an origin URL without credentials or query parameters.')
    return defaults
def tool(name,default=None):
    return load()['tools'].get(name) or shutil.which(name) or default
def browser_executable():
    # Playwright's installed browser is the portable default. Arbitrary system
    # Chromium/Edge wrappers can mismatch the tested protocol/build. Preserve
    # explicit native overrides, including the owner's NixOS configuration.
    return load()['tools'].get('chromium') or os.environ.get('STUDY_CHROMIUM','')
def browser_validation_env():
    return {**os.environ,'STUDY_CHROMIUM':browser_executable(),
            'STUDY_PLAYWRIGHT_MODULE':tool('playwright-module','playwright')}
def library_root():return Path(load()['library_root'])
def origin(which='backend'):return load()[which+'_url'].rstrip('/')
