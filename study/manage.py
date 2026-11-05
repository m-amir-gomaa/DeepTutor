#!/usr/bin/env python3
"""Portable study setup. No auth import, cloud spending or learner ratings."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
from urllib.request import Request,urlopen
import study_settings

ROOT=Path(__file__).resolve().parent
def atomic(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    import tempfile
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.study-')
    try:
        with os.fdopen(fd,'w') as f:os.fchmod(f.fileno(),0o600);f.write(text)
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()
def save(path,data):atomic(path,json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def api(path,data=None,method='GET'):
    req=Request(study_settings.origin()+path,data=None if data is None else json.dumps(data).encode(),method=method,
                headers={'Content-Type':'application/json','Origin':study_settings.origin('frontend')})
    with urlopen(req,timeout=45) as response:return json.load(response)
def existing_workspace(record,existing):
    stored=record.get('workspace')
    if stored:
        bound=stored.get('workspace',stored);identity=bound.get('workspace_id')
        found=next((w for w in existing if w['workspace_id']==identity),None)
        if not found:raise ValueError('Stored DeepTutor workspace is missing; preserve the mapping and restore it before attaching.')
        return found
    content_path=record.get('content_path',record['path'])
    return next((w for w in existing if str(Path(w['path']).resolve())==str(Path(content_path).resolve())),None)
def initialize(profile,name,slug=None,library_root=None):
    from setup_center import profiles
    all_profiles=profiles()
    if profile not in all_profiles:raise ValueError('Unknown discipline profile.')
    slug=slug or re.sub('[^a-z0-9-]+','-',name.lower()).strip('-')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,69}',slug):raise ValueError('Use a short lowercase vault slug.')
    if not name.strip() or len(name)>100:raise ValueError('Use a name of 1–100 characters.')
    path=study_settings.config_path();conf=study_settings.load()
    if library_root:
        new_root=str(Path(library_root).expanduser().resolve())
        if path.exists() and new_root!=conf['library_root']:raise ValueError('Existing library root preserved. Use a separate configuration for a separate learner.')
        conf['library_root']=new_root
    if not path.exists():save(path,conf)
    base=Path(conf['library_root']);control=base/'.control';control.mkdir(parents=True,exist_ok=True,mode=0o700)
    records_path=control/'vaults.json';rows=json.loads(records_path.read_text()) if records_path.exists() else {}
    if slug in rows:
        return {'status':'already prepared','vault':slug,'path':rows[slug]['path'],'learner_files_preserved':True}
    root=base/slug;root.mkdir(parents=True,exist_ok=True,mode=0o700)
    for child in ['.study','inbox','references','sources','library','concepts','problems','sessions','reviews','visuals']:
        (root/child).mkdir(mode=0o700,exist_ok=True)
    p=all_profiles[profile]
    files={'HOME.md':f'# {name}\n\nUse the Study setup prompt library. Add owned PDFs to inbox/.\n',
           'LEARNER.md':f'# {name}: learner preferences\n\nGoal: {p["goal"]}\n\nTeaching: {p["teaching"]}\n\nVisuals: {p["visuals"]}\n\nLanguage: choose with the learner.\nPacing: learner-controlled; complete examples before concise checks.\nNew courses require an explicit scope choice.\n',
           'STATE.md':'# Study state\n\nNew vault. No reading, attempt, mastery or review is recorded.\n',
           'RESUME.md':'# Resume\n\nImport a source, agree on its introductory unit and begin.\n',
           '.study/sources.json':'[]\n',
           '.study/curriculum.json':json.dumps({'version':1,'position':0,'units':[{'id':'first-unit','title':'Plan the introductory unit','sources':[],'ranges':[]}],'transitions':[]},indent=2)+'\n',
           'library/STUDY-PREPARATION.md':f'# {name}: preparation\n\nDiscipline: {profile}. No source has been assigned yet.\nImport the actual edition and plan its introductory unit with the learner.\n',
           'library/BOOK-ATLAS.md':'# Registered books\n\n[[../REGISTRY]] is the current generated source list. Use the actual source IDs, editions and physical-page bookmarks when planning a unit. Catalogue entries are not acquired books.\n'}
    for relative,text in files.items():
        target=root/relative
        if target.exists():continue
        atomic(target,text)
    for guide in ['SETUP-HUMAN.md','SETUP-AGENT.md']:
        atomic(root/'library'/guide,(ROOT/guide).read_text())
    for alias in ['STUDY-SYSTEM-GUIDE.md']:
        atomic(root/'library'/alias,(ROOT/'SETUP-HUMAN.md').read_text())
    content=base/'.workspaces'/slug;content.mkdir(parents=True,exist_ok=True,mode=0o700)
    rows[slug]={'name':name,'path':str(root),'content_path':str(content),'profile':profile};save(records_path,rows)
    tools=control/'native-tools.json'
    if not tools.exists():save(tools,{'python3':sys.executable,**{k:shutil.which(k) for k in ['bwrap','manim','cli-anything-inkscape']}})
    return {'status':'prepared','vault':slug,'path':str(root),'profile':profile,'cloud_enabled':conf['modal']['enabled'],
            'next':'Start DeepTutor with the same private runtime home; run manage.py attach, authorize a model and import owned PDFs.'}
def attach():
    from setup_center import profiles
    conf=study_settings.load();base=Path(conf['library_root']);path=base/'.control/vaults.json';rows=json.loads(path.read_text())
    skills={s['name'] for s in api('/api/skills/list')['skills']}
    for file in sorted((ROOT/'skills').glob('*/SKILL.md')):
        name=file.parent.name;text=file.read_text();desc=text.split('description: ',1)[1].split('\n',1)[0]
        if name in skills:api('/api/skills/'+name,{'content':text},'PUT')
        else:api('/api/skills/create',{'name':name,'description':desc,'content':text,'tags':['study']},'POST')
    existing=api('/api/settings/workspace/registrations')['workspaces'];result=[]
    for slug,record in rows.items():
        root=Path(record['path']);profile=profiles()[record.get('profile','general')]
        instructions=(root/'LEARNER.md').read_text()+'\nUse the scoped study service: orientation, learning_path, source_page, notes/cards and study_setup. Read library/SETUP-HUMAN.md for operation. In a new vault use plan_first_unit only for the learner-selected introductory source. Never invent readiness, learner answers or reviews.\n'
        service='study_'+slug.replace('-','_')
        env={'DEEPTUTOR_STUDY_CONFIG':str(study_settings.config_path().resolve()),'PYTHONUNBUFFERED':'1',
             'STUDY_PYTHON':conf['python'],'PATH':str(Path(conf['python']).parent)+os.pathsep+os.environ.get('PATH','')}
        if conf['native_library_path']:env['LD_LIBRARY_PATH']=conf['native_library_path']
        api('/api/settings/mcp/servers/'+service,{'type':'stdio','command':conf['python'],'args':[str(ROOT/'study_tools.py'),'--vault',slug],
                                              'env':env,'enabled':True,'tool_timeout':390},'PUT')
        catalog=api('/api/settings/workspace/resources');available_skills={r['id'] for r in catalog['skills']};available_mcp={r['name']:r['id'] for r in catalog['mcp']}
        current=existing_workspace(record,existing)
        prior=(current or {}).get('resources',{})
        selected=list(dict.fromkeys([*prior.get('skills',[]),*[x for x in profile['skills'] if x in available_skills]]))
        mcp=list(dict.fromkeys([*prior.get('mcp',[]),available_mcp[service],*[available_mcp[x] for x in profile['research_services']+['study_anki'] if x in available_mcp]]))
        resources={**prior,'skills':selected,'mcp':mcp}
        body={'name':record['name'],'instructions':instructions,'resources':resources}
        if current:
            saved=api('/api/settings/workspace/registrations/'+current['workspace_id'],body,'PATCH')
        else:saved=api('/api/settings/workspace/registrations',{**body,'path':record.get('content_path',str(root))},'POST')
        record['workspace']=saved;record['mcp_name']=service;save(path,rows)
        result.append({'vault':slug,'workspace':saved.get('workspace',saved)['workspace_id'],
                       'missing_optional_services':[x for x in profile['research_services']+['study_anki'] if x not in available_mcp]})
    return result
def doctor():
    conf=study_settings.load();base=Path(conf['library_root']);services={}
    for name,url in [('backend',conf['backend_url']+'/api/tools'),('frontend',conf['frontend_url']+'/')]:
        try:
            with urlopen(url,timeout=3) as r:services[name]=r.status==200
        except Exception:services[name]=False
    return {'python':sys.version.split()[0],'library_prepared':(base/'.control/vaults.json').is_file(),
            'local_services':services,'executables':{name:bool(study_settings.tool(name)) for name in ['bwrap','manim','ffmpeg','inkscape','drawio','mineru-kit','node']},
            'cloud_enabled':conf['modal']['enabled'],'model_or_ocr_invoked':False,
            'scope':'Presence and local HTTP readiness only; no authentication or feature acceptance is inferred.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('--profile',default='general');init.add_argument('--name',default='Study');init.add_argument('--slug');init.add_argument('--library-root')
    sub.add_parser('attach');sub.add_parser('doctor');sub.add_parser('open')
    args=p.parse_args()
    if args.command=='init':result=initialize(args.profile,args.name,args.slug,args.library_root)
    elif args.command=='attach':result=attach()
    elif args.command=='doctor':result=doctor()
    else:
        import webbrowser
        url=study_settings.origin('frontend')+'/api/settings/study/page';webbrowser.open(url);result={'opened':url}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
