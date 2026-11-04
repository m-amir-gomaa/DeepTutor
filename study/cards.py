"""Durable, scoped Anki outbox with exact-Key reconciliation after timeouts.

The model cannot supply another deck, rating action, arbitrary tool or local key.
"""
import asyncio
import hashlib
import json
import re
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from library import CONTROL, records, vault, now
from progress import db_for

FIELDS={'Prompt','Answer','Why','Source','Track','Key'}
def database(slug):
    db=db_for(slug)
    db.executescript('''CREATE TABLE IF NOT EXISTS card_outbox(key TEXT PRIMARY KEY,fields TEXT,sha256 TEXT,status TEXT,note_id INTEGER,error TEXT,updated TEXT);
    CREATE TABLE IF NOT EXISTS card_revisions(key TEXT,previous TEXT,replacement TEXT,created TEXT);''')
    return db

def queue(slug,cards):
    if not 1<=len(cards)<=5:raise ValueError('Queue a small batch of one to five cards')
    results=[];track=records()[slug]['name']
    with database(slug) as db:
        for fields in cards:
            fields={**fields,'Track':track}
            if set(fields)!=FIELDS or any(not isinstance(v,str) or len(v)>16000 for v in fields.values()):raise ValueError('Use Prompt, Answer, Why, Source, Track and Key string fields')
            key=fields['Key']
            if not re.fullmatch('[a-z0-9][a-z0-9-]{2,100}',key) or not fields['Prompt'].strip() or not fields['Answer'].strip() or not fields['Source'].strip():raise ValueError('Require a stable Key, retrieval prompt, answer and source')
            if len(fields['Prompt'])>600 or len(fields['Answer'])>1800 or len(fields['Why'])>1200:
                raise ValueError('Split this proposal into one concise retrieval target; keep the explanation in the linked note')
            if not fields['Why'].strip() or fields['Prompt'].strip().casefold()==fields['Answer'].strip().casefold():
                raise ValueError('Supply a retrieval answer and a useful reason/counterexample, not a repeated prompt')
            if any('```' in fields[k] or re.search(r'\$[^$\n]+\$',fields[k]) for k in ['Prompt','Answer','Why']):
                raise ValueError('Anki uses simple HTML and MathJax delimiters, not Markdown fences or dollar math')
            if any(re.search(r'<\s*(script|iframe|object|embed)|\bon\w+\s*=|javascript:',v,re.I) for v in fields.values()):raise ValueError('Use simple Anki HTML without executable content')
            data=json.dumps(fields,sort_keys=True);sha=hashlib.sha256(data.encode()).hexdigest()
            old=db.execute('SELECT * FROM card_outbox WHERE key=?',(key,)).fetchone()
            if old and old['sha256']!=sha:raise ValueError('Stable Key has different content; use an explicit repair or version rather than duplicating it')
            db.execute('INSERT OR IGNORE INTO card_outbox VALUES(?,?,?,?,?,?,?)',(key,data,sha,'pending',None,'',now()))
            results.append({'key':key,'status':old['status'] if old else 'pending'})
    return results

async def call(session,name,args):
    r=await session.call_tool(name,args)
    if r.isError:raise RuntimeError('Anki '+name+' failed')
    texts=[c.text for c in r.content if hasattr(c,'text')]
    if len(texts)!=1:raise RuntimeError('Unexpected Anki result shape')
    return json.loads(texts[0])

async def flush(slug):
    results=[];track=records()[slug]['name'];deck='Study::'+track
    # Two repeated lesson turns cannot race the stable-Key lookup/add pair.
    from library import lock
    with lock(),database(slug) as db:
        pending=db.execute('SELECT * FROM card_outbox WHERE status="pending" ORDER BY updated LIMIT 5').fetchall()
        if not pending:return {'outcomes':[],'status':'no pending cards'}
        try:
            key=(CONTROL/'anki-local-key').read_text().strip()
            async with streamablehttp_client('http://127.0.0.1:3141/',headers={'Authorization':'Bearer '+key}) as (r,w,_):
                async with ClientSession(r,w) as s:
                    await s.initialize()
                    for row in pending:
                        fields=json.loads(row['fields'])
                        found=await call(s,'find_notes',{'query':'deck:"'+deck+'" Key:'+row['key'],'limit':10})
                        ids=found.get('noteIds',[]);exact=[]
                        if ids:
                            info=await call(s,'notes_info',{'notes':ids})
                            exact=[n for n in info['notes'] if n['fields'].get('Key',{}).get('value')==row['key']]
                        if len(exact)>1:raise RuntimeError('Multiple exact stable Keys; manual reconciliation required')
                        if exact:
                            n=exact[0];note_id=n['noteId']
                            actual={k:n['fields'].get(k,{}).get('value','') for k in FIELDS}
                            if actual!=fields:
                                db.execute('UPDATE card_outbox SET status="conflict",note_id=?,error=?,updated=? WHERE key=?',(note_id,'Existing card content differs; preserved',now(),row['key']))
                                results.append({'key':row['key'],'status':'conflict; existing card preserved'});continue
                            status='already present'
                        else:
                            added=await call(s,'add_note',{'deck_name':deck,'model_name':'Study Concept','fields':fields,'tags':['study_generated'],'allow_duplicate':False})
                            note_id=added.get('noteId',added.get('note_id',added.get('id')))
                            status='added'
                        db.execute('UPDATE card_outbox SET status="synced",note_id=?,error="",updated=? WHERE key=?',(note_id,now(),row['key']))
                        db.commit();results.append({'key':row['key'],'status':status,'note_id':note_id})
        except Exception as e:
            # A timed-out add may have succeeded remotely. Leave it pending;
            # the next run repeats the exact-Key lookup before any add.
            db.execute('UPDATE card_outbox SET error=?,updated=? WHERE status="pending"',(type(e).__name__+'; retry checks exact Key before adding',now()))
            results.append({'status':'pending; Anki unavailable or response interrupted','error_type':type(e).__name__})
    return {'outcomes':results,'deck':deck,'ratings_changed':False}

def status(slug):
    with database(slug) as db:return [dict(r) for r in db.execute('SELECT key,status,note_id,error,updated FROM card_outbox ORDER BY updated DESC LIMIT 15')]
