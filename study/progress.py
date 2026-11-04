"""Transactional learning records. No inferred scores or automated Anki ratings."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
from library import atomic, now, vault, sources, write_json

def db_for(slug):
    p=vault(slug)/'.study/progress.sqlite3';db=sqlite3.connect(p,timeout=30);p.chmod(0o600)
    db.row_factory=sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,path TEXT,title TEXT,revision INTEGER,content TEXT,sha256 TEXT,status TEXT);
      CREATE TABLE IF NOT EXISTS revisions(id TEXT,revision INTEGER,content TEXT,created TEXT,PRIMARY KEY(id,revision));
      CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT,created TEXT,payload TEXT);
      CREATE TABLE IF NOT EXISTS checkpoints(id TEXT PRIMARY KEY,created TEXT,payload TEXT);
      CREATE TABLE IF NOT EXISTS practice(id TEXT PRIMARY KEY,created TEXT,due TEXT,source_id TEXT,prompt TEXT,status TEXT);
    ''')
    return db

def flush_notes(slug):
    root=vault(slug);written=[]
    with db_for(slug) as db:
        for row in db.execute('SELECT * FROM notes WHERE status="pending"').fetchall():
            p=root/row['path']
            # A retry may find exactly the bytes written before an interrupted DB acknowledgement.
            if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
                old=db.execute('SELECT content FROM revisions WHERE id=? AND revision=?',(row['id'],row['revision']-1)).fetchone()
                if not old or p.read_text()!=old[0]:
                    raise ValueError('Manual note edit detected; preserved '+row['path']+'. Read and reconcile before saving another revision.')
            atomic(p,row['content']);db.execute('UPDATE notes SET status="written" WHERE id=?',(row['id'],));written.append(row['path'])
    return written

def save_note(slug,kind,title,body,refs=None,concept_id=None):
    if kind not in {'concepts','problems','sessions','reviews'} or not 1<=len(title)<=140 or len(body)>30000:
        raise ValueError('Use a short title and a concept/problem/session/review under 30 KB')
    key=concept_id or kind+'-'+hashlib.sha256(title.casefold().encode()).hexdigest()[:16]
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,100}',key):raise ValueError('Use a stable lowercase concept ID')
    name=re.sub('[^a-z0-9-]+','-',title.casefold()).strip('-')[:60] or 'note'
    relative=kind+'/'+name+'-'+key[-12:]+'.md'
    content='---\nconcept_id: '+key+'\nkind: '+kind+'\ngenerated_draft: true\n---\n\n# '+title+'\n\n'+body+'\n\n## Sources\n\n'+'\n'.join('- '+x for x in (refs or []))+'\n'
    sha=hashlib.sha256(content.encode()).hexdigest()
    with db_for(slug) as db:
        row=db.execute('SELECT * FROM notes WHERE id=?',(key,)).fetchone()
        if row and row['status']=='archived_setup':raise ValueError('This generated setup note was archived; use the current unit note or deliberately restore the archive')
        if row and row['path'].split('/')[0]!=kind:raise ValueError('Concept ID belongs to a different note kind')
        if row:relative=row['path']
        revision=(row['revision'] if row and row['sha256']==sha else (row['revision']+1 if row else 1))
        if not row or row['sha256']!=sha:
            path=vault(slug)/relative
            if path.exists() and (not row or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']):
                raise ValueError('Manual content preserved; reconcile the existing note before replacement')
            db.execute('INSERT INTO revisions VALUES(?,?,?,?)',(key,revision,content,now()))
            db.execute('INSERT OR REPLACE INTO notes VALUES(?,?,?,?,?,?,?)',(key,relative,title,revision,content,sha,'pending'))
    flush_notes(slug)
    # A generated navigation index avoids ever-growing duplicate STATE appends.
    with db_for(slug) as db:rows=db.execute('SELECT id,path,title,revision FROM notes WHERE status!="archived_setup" ORDER BY title').fetchall()
    atomic(vault(slug)/'library/GENERATED-NOTES.md','# Generated study notes\n\nDraft notes and revisions; no mastery inferred.\n\n'+'\n'.join('- [['+r['path'][:-3]+'|'+r['title']+']] — `'+r['id']+'` rev '+str(r['revision']) for r in rows)+'\n')
    return {'saved':relative,'concept_id':key,'revision':revision,'status':'generated draft','obsidian_url':note_uri(slug,relative)}

def note_uri(slug,relative='HOME.md'):
    root=vault(slug);p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()) or any(x.startswith('.') for x in Path(relative).parts):raise ValueError('Use a vault note')
    return 'obsidian://open?path='+quote(str(p),safe='')

def checkpoint(slug,unit,source_id=None,pdf_page=None,pending_question='',next_action='',session_id=''):
    if source_id:
        s=next((s for s in sources(slug) if s['id']==source_id),None)
        if not s:raise ValueError('Unregistered source')
        if pdf_page is not None and not 1<=pdf_page<=s['pdf_pages']:raise ValueError('Page outside source')
    payload={'unit':unit[:240],'source_id':source_id,'pdf_page':pdf_page,
             'pending_question':pending_question[:6000],'next_action':next_action[:4000],'session_id':session_id[:160],
             'assessment':'No mastery inferred from this checkpoint'}
    key=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    with db_for(slug) as db:
        db.execute('INSERT OR IGNORE INTO checkpoints VALUES(?,?,?)',(key,now(),json.dumps(payload)))
    write_json(vault(slug)/'.study/checkpoint.json',{'id':key,'saved_at':now(),**payload})
    atomic(vault(slug)/'RESUME.md','# Resume this subject\n\nUnit: '+unit+'\n\nSource: '+str(source_id)+' — PDF page '+str(pdf_page)+'\n\n## Waiting for you\n\n'+(pending_question or 'No pending question recorded.')+'\n\n## Next action\n\n'+next_action+'\n\nNo mastery inferred. The original conversation remains available.\n')
    return {'id':key,'status':'checkpoint saved',**payload}

def evidence(slug,kind,concept_id,learner_text,source_ref='',assistance='unspecified'):
    if kind not in {'self_report','learner_attempt','hint_assisted_attempt','delayed_check','feedback'}:
        raise ValueError('Use an explicit evidence type, not a mastery score')
    if not learner_text.strip() or len(learner_text)>14000:raise ValueError('Preserve the actual answer or owner statement')
    payload={'concept_id':concept_id,'learner_text':learner_text,'source_ref':source_ref,'assistance':assistance,
             'meaning':'Recorded evidence; no automatic mastery certification'}
    key=hashlib.sha256(json.dumps([kind,payload],sort_keys=True).encode()).hexdigest()
    with db_for(slug) as db:db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?)',(key,kind,now(),json.dumps(payload)))
    return {'id':key,'kind':kind,'status':'recorded'}

def queue_practice(slug,source_id,prompt,days=2):
    if source_id not in {s['id'] for s in sources(slug)}:raise ValueError('Unregistered source')
    if not prompt.strip() or len(prompt)>6000 or not 1<=days<=180:raise ValueError('Use one bounded task, due in 1–180 days')
    key=hashlib.sha256((source_id+'\n'+prompt).encode()).hexdigest()[:24]
    due=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
    with db_for(slug) as db:
        db.execute('INSERT OR IGNORE INTO practice VALUES(?,?,?,?,?,?)',(key,now(),due,source_id,prompt,'pending'))
        row=dict(db.execute('SELECT * FROM practice WHERE id=?',(key,)).fetchone())
    return row

def status(slug):
    root=vault(slug);p=root/'.study/checkpoint.json'
    with db_for(slug) as db:
        due=[dict(r) for r in db.execute('SELECT * FROM practice WHERE status="pending" AND due<=? ORDER BY due LIMIT 10',(now(),))]
        counts={r['kind']:r['n'] for r in db.execute('SELECT kind,count(*) n FROM events GROUP BY kind')}
    return {'checkpoint':json.loads(p.read_text()) if p.exists() else None,'due_practice':due,'evidence_counts':counts}

def complete_practice(slug,practice_id,learner_text,assistance='unspecified',needs_review=False):
    with db_for(slug) as db:
        task=db.execute('SELECT * FROM practice WHERE id=?',(practice_id,)).fetchone()
        if not task:raise ValueError('Unknown delayed practice task')
    result=evidence(slug,'delayed_check',practice_id,learner_text,task['source_id'],assistance)
    with db_for(slug) as db:
        db.execute('UPDATE practice SET status=? WHERE id=?',('needs_review' if needs_review else 'attempted',practice_id))
    return {'practice_id':practice_id,'status':'needs_review' if needs_review else 'attempted','evidence_id':result['id'],'mastery_inferred':False}

def canvas(slug,title,nodes,edges):
    if not 1<=len(nodes)<=16 or len(edges)>30:raise ValueError('Use a focused map of 1–16 concepts and at most 30 relations')
    root=vault(slug);out=[];ids=set()
    for n,row in enumerate(nodes):
        key=str(row.get('id',n));ids.add(key)
        item={'id':key,'x':(n%3)*390,'y':(n//3)*230,'width':330,'height':170}
        if row.get('note'):
            rel=row['note'];path=(root/rel).resolve()
            if not path.is_relative_to(root.resolve()) or path.suffix!='.md' or any(p.startswith('.') for p in Path(rel).parts) or not path.is_file():raise ValueError('Use an existing vault Markdown note')
            item.update(type='file',file=rel)
        else:item.update(type='text',text=row.get('label','')[:1000])
        out.append(item)
    links=[]
    for i,e in enumerate(edges):
        if str(e['from']) not in ids or str(e['to']) not in ids:raise ValueError('Edge references absent node')
        links.append({'id':'edge-'+str(i),'fromNode':str(e['from']),'fromSide':'right','toNode':str(e['to']),'toSide':'left','label':e.get('label','relates to')[:160]})
    key=re.sub('[^a-z0-9]+','-',title.casefold()).strip('-')[:60] or 'concept-map'
    relative='visuals/'+key+'.canvas';write_json(root/relative,{'nodes':out,'edges':links})
    return {'path':relative,'obsidian_url':note_uri(slug,relative),'editable':True,'status':'generated conceptual map; inspect relationships'}
