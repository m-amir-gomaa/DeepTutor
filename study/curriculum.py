"""Small ordered lesson routes; acquired references never imply unlocked courses."""
import json,re
from pathlib import Path
import library, progress

def path(slug):return library.vault(slug)/'.study/curriculum.json'
def first_unit(slug,source_id,first,last,title):
    source=next((s for s in library.sources(slug) if s['id']==source_id),None)
    if not source or type(first) is not int or type(last) is not int or not 1<=first<=last<=source['pdf_pages'] or last-first>=40:
        raise ValueError('Choose a registered source and one introductory block of at most forty physical pages.')
    if not isinstance(title,str) or not 4<=len(title.strip())<=200:raise ValueError('Use a descriptive unit title.')
    with library.lock():
        p=path(slug);d=json.loads(p.read_text())
        if d['position']!=0 or len(d['units'])!=1 or d['units'][0].get('sources') or d.get('transitions'):
            raise ValueError('An existing course route is configured; preserve it.')
        with progress.db_for(slug) as db:
            if db.execute('SELECT count(*) FROM events').fetchone()[0]:raise ValueError('Learner evidence exists; preserve and review the current route.')
        d['units'][0]={'id':'first-unit','title':title.strip(),'sources':[source_id],
                       'ranges':[{'source':source_id,'first':first,'last':last}],
                       'planned_at':library.now(),'mastery_claimed':False}
        library.write_json(p,d)
    return status(slug)
def status(slug):
    p=path(slug)
    if not p.exists():return {'configured':False,'allowed_sources':None}
    d=json.loads(p.read_text());units=d['units'];i=d['position']
    return {'configured':True,'current':units[i], 'position':i,
            'allowed_ranges':[r for u in units[:i+1] for r in u.get('ranges',[])],
            'allowed_sources':list(dict.fromkeys(s for u in units[:i+1] for s in u.get('sources',[]))),
            'next_locked':[{'id':u['id'],'title':u['title'],'requires':units[n-1]['id']} for n,u in enumerate(units) if n>i],
            'meaning':'Prepared/current is not mastery. Advance only from actual learner evidence or an explicit learner readiness statement.'}
def allowed(slug,source_id,page=None):
    d=status(slug);ids=d['allowed_sources']
    if ids is None:return True
    if source_id not in ids:return False
    ranges=[r for r in d['allowed_ranges'] if r['source']==source_id]
    return page is None or not ranges or any(r['first']<=page<=r['last'] for r in ranges)
def require(slug,source_id,page=None):
    if not allowed(slug,source_id,page):raise ValueError('This reference/page is locked by the current learning route. Stay with the current unit returned by learning_path.')
def extend(slug,unit_id,title,ranges):
    """Append one bounded chronological unit; no unlock or evidence fabricated.

    Only existing route sources, and only consecutive physical pages, are accepted.
    This lets the tutor continue beyond setup's three units without operator edits.
    """
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,79}',unit_id) or not isinstance(title,str) or not 4<=len(title.strip())<=200:
        raise ValueError('Use a stable lowercase unit ID and a descriptive title.')
    if not isinstance(ranges,list) or not 1<=len(ranges)<=3:raise ValueError('Use one to three source-page ranges.')
    with library.lock():
        p=path(slug);d=json.loads(p.read_text());units=d['units']
        if d['position']!=len(units)-1:raise ValueError('Existing planned units remain. Continue them before extending the route.')
        if any(u['id']==unit_id for u in units):raise ValueError('Unit ID already exists.')
        books={s['id']:s for s in library.sources(slug)};last={}
        for u in units:
            for r in u.get('ranges',[]):last[r['source']]=max(last.get(r['source'],0),r['last'])
        checked=[]
        for r in ranges:
            source=r.get('source');first=r.get('first');end=r.get('last')
            if source not in last or source not in books:raise ValueError('Only a source already on this route can be extended. New courses need an explicit scope decision.')
            if type(first) is not int or type(end) is not int or first!=last[source]+1 or not first<=end<=books[source]['pdf_pages'] or end-first>=40:
                raise ValueError('Continue with the next physical page, at most forty pages per source, within the registered PDF.')
            checked.append({'source':source,'first':first,'last':end});last[source]=end
        if len({r['source'] for r in checked})!=len(checked):raise ValueError('Use at most one range per source.')
        d['units'].append({'id':unit_id,'title':title.strip(),'sources':[r['source'] for r in checked],
                           'ranges':checked,'planned_at':library.now(),'planned_by':'tutor','mastery_claimed':False})
        library.write_json(p,d)
    return status(slug)
def advance(slug,evidence_id):
    with library.lock(),progress.db_for(slug) as db:
        p=path(slug);d=json.loads(p.read_text());i=d['position']
        row=db.execute('SELECT kind,payload FROM events WHERE id=?',(evidence_id,)).fetchone()
        if not row or row['kind'] not in {'self_report','learner_attempt','delayed_check','hint_assisted_attempt'}:
            raise ValueError('Use an existing real learner evidence ID, never a generated demonstration or feedback event')
        payload=json.loads(row['payload'])
        if payload.get('concept_id')!=d['units'][i]['id']:
            raise ValueError('Evidence must refer to the current unit ID')
        if i+1>=len(d['units']):raise ValueError('No next unit configured; extend the route deliberately')
        d.setdefault('transitions',[]).append({'from':d['units'][i]['id'],'to':d['units'][i+1]['id'],'evidence_id':evidence_id,'at':library.now(),'mastery_claimed':False})
        d['position']=i+1;library.write_json(p,d)
    return status(slug)
