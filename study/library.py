#!/usr/bin/env python3
"""Private, offline book intake, registry views and incremental SQLite page search.

Source JSON remains interoperable with the original study service. No PDF is sent
to a model by this program. Original owner files and startup catalogues are read only.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import pymupdf
import study_settings

BASE = study_settings.library_root()
CONTROL = BASE / '.control'
STARTUP = Path(study_settings.load()['startup_catalogue_root'])

def now(): return datetime.now(timezone.utc).isoformat()
def records(): return json.loads((CONTROL/'vaults.json').read_text())
def vault(slug):
    if slug not in records(): raise ValueError('Unknown vault')
    return Path(records()[slug]['path'])
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def atomic(path, content):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.write-')
    try:
        with os.fdopen(fd,'w') as f:
            os.fchmod(f.fileno(),0o600);f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()
def write_json(path,data): atomic(path,json.dumps(data,indent=2,ensure_ascii=False)+'\n')
@contextmanager
def lock():
    CONTROL.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (CONTROL/'library.lock').open('a') as f:
        os.fchmod(f.fileno(),0o600);fcntl.flock(f,fcntl.LOCK_EX)
        yield

def sources(slug): return json.loads((vault(slug)/'.study/sources.json').read_text())
def connection():
    db=sqlite3.connect(CONTROL/'library.sqlite3',timeout=90)
    (CONTROL/'library.sqlite3').chmod(0o600)
    db.row_factory=sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS books(vault TEXT,id TEXT,title TEXT,pdf TEXT,sha256 TEXT,pages INTEGER,indexed_at TEXT,PRIMARY KEY(vault,id));
      CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(vault UNINDEXED,source_id UNINDEXED,page UNINDEXED,text,tokenize='unicode61 remove_diacritics 2');
      CREATE TABLE IF NOT EXISTS contents(vault TEXT,source_id TEXT,level INTEGER,title TEXT,page INTEGER);
      CREATE TABLE IF NOT EXISTS catalogue(registry_id TEXT PRIMARY KEY,scope TEXT,topic TEXT,title TEXT,authors TEXT,edition TEXT,source_url TEXT,direct_download_url TEXT,target_directory TEXT,pdf_filename TEXT,selection_role TEXT,acquisition_status TEXT,processing_permission TEXT,origin TEXT);
    ''')
    return db

def import_pdf(slug, path, title=None, source_id=None, role='reference', source_url='', from_inbox=False):
    root=vault(slug);path=Path(path).expanduser().resolve()
    if from_inbox and not path.is_relative_to((root/'inbox').resolve()):
        raise ValueError('Import only a PDF inside this vault inbox')
    if path.suffix.lower()!='.pdf' or not path.is_file() or path.stat().st_size>512*1024**2:
        raise ValueError('Use a local PDF no larger than 512 MiB')
    sha=digest(path)
    with pymupdf.open(path) as doc:
        if doc.is_encrypted:raise ValueError('Unlock the PDF yourself before intake')
        if not 1<=len(doc)<=50000:raise ValueError('Unreasonable PDF page count')
        pages=len(doc);meta=doc.metadata or {};toc=doc.get_toc()
        # Require an actual readable first page; scanned books can still use image retrieval.
        doc[0].get_text()
    stem=re.sub('[^a-z0-9-]+','-',(title or path.stem).lower()).strip('-')[:55] or 'book'
    source_id=source_id or stem+'-'+sha[:10]
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,100}',source_id):raise ValueError('Use a short lowercase source ID')
    with lock():
        current=sources(slug)
        same=next((s for s in current if s['sha256']==sha),None)
        if same:return {'status':'already registered','source':same}
        if any(s['id']==source_id for s in current):raise ValueError('Source ID belongs to different bytes; use a distinct edition ID')
        target=root/'references'/(source_id+'.pdf')
        if target.exists() and digest(target)!=sha:raise ValueError('Destination conflict; original preserved')
        if not target.exists():
            fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.import-');os.close(fd)
            try:
                shutil.copyfile(path,tmp)
                if digest(tmp)!=sha:raise ValueError('Copy verification failed')
                Path(tmp).chmod(0o400);os.replace(tmp,target)
            finally:
                if Path(tmp).exists():Path(tmp).unlink()
        item={'id':source_id,'title':title or meta.get('title') or path.stem,'pdf':str(target),
              'original':str(path),'pdf_pages':pages,'sha256':sha,'source_url':source_url,
              'role':role,'registered_at':now(),'boundary_status':'not_fully_reviewed',
              'rights_status':'owner_local_private_reference_no_publication_rights_inferred'}
        current.append(item);write_json(root/'.study/sources.json',current)
        content='# '+item['title']+' — contents\n\nSource ID: `'+source_id+'`\n\nPhysical PDF pages, not printed pagination. Import is not learning evidence.\n\n'
        content+='\n'.join('- '+('  '*max(0,int(level)-1))+str(heading)+' — PDF p. '+str(page) for level,heading,page in toc)
        if not toc:content+='No PDF bookmarks; use full-text search and inspect the actual pages.'
        atomic(root/'library'/(source_id+'-contents.md'),content+'\n')
    return {'status':'registered','source':item}

def intake(slug):
    root=vault(slug);inbox=root/'inbox';inbox.mkdir(mode=0o700,exist_ok=True)
    receipts=[]
    last=root/'.study/intake-receipt.json'
    previous={r['file']:r for r in json.loads(last.read_text()).get('files',[])} if last.exists() else {}
    for p in sorted(inbox.glob('*')):
        if p.is_file() and p.suffix.lower()=='.pdf':
            stat=p.stat();signature=[stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns]
            old=previous.get(p.name)
            if old and old.get('signature')==signature and old.get('status') in {'registered','already registered'}:
                receipts.append({**old,'status':'already registered'});continue
            try:receipts.append({'file':p.name,'signature':signature,**import_pdf(slug,p,from_inbox=True)})
            except Exception as e:receipts.append({'file':p.name,'signature':signature,'status':'needs attention','error':str(e)[:350]})
    write_json(root/'.study/intake-receipt.json',{'checked_at':now(),'files':receipts})
    return receipts

def index(slug=None):
    counts={'indexed_sources':0,'skipped_sources':0,'pages':0,'errors':[]}
    with lock(), connection() as db:
        for key in ([slug] if slug else records()):
            root=vault(key)
            for s in sources(key):
                previous=db.execute('SELECT sha256 FROM books WHERE vault=? AND id=?',(key,s['id'])).fetchone()
                if previous and previous[0]==s['sha256']:
                    counts['skipped_sources']+=1;continue
                try:
                    with pymupdf.open(s['pdf']) as doc:
                        pages=[]
                        for n,p in enumerate(doc,1):
                            prepared=root/'sources'/s['id']/f'page-{n:04d}.md'
                            text=prepared.read_text() if prepared.exists() else p.get_text()
                            pages.append((key,s['id'],n,text))
                        toc=[(key,s['id'],*row) for row in doc.get_toc()]
                    db.execute('SAVEPOINT source_index')
                    db.execute('DELETE FROM pages WHERE vault=? AND source_id=?',(key,s['id']))
                    db.execute('DELETE FROM contents WHERE vault=? AND source_id=?',(key,s['id']))
                    db.executemany('INSERT INTO pages VALUES(?,?,?,?)',pages)
                    db.executemany('INSERT INTO contents VALUES(?,?,?,?,?)',toc)
                    db.execute('INSERT OR REPLACE INTO books VALUES(?,?,?,?,?,?,?)',(key,s['id'],s['title'],s['pdf'],s['sha256'],len(pages),now()))
                    db.execute('RELEASE source_index')
                    db.commit()
                    counts['indexed_sources']+=1;counts['pages']+=len(pages)
                except Exception as e:
                    db.rollback();counts['errors'].append({'vault':key,'id':s['id'],'error':str(e)[:300]})
    write_json(CONTROL/'last-index.json',{'at':now(),**counts})
    return counts

def search(query, slug=None, source_id=None, limit=8, page_ranges=None):
    words=re.findall(r'\w+',query,flags=re.UNICODE)[:16]
    if not words:raise ValueError('Supply search words')
    clauses=[];params=[]
    if slug:vault(slug);clauses.append('p.vault=?');params.append(slug)
    if source_id:clauses.append('p.source_id=?');params.append(source_id)
    if page_ranges is not None:
        if not page_ranges:return []
        clauses.append('('+' OR '.join('(p.source_id=? AND CAST(p.page AS INTEGER) BETWEEN ? AND ?)' for r in page_ranges)+')')
        for r in page_ranges:params.extend([r['source'],r['first'],r['last']])
    if not source_id:
        # Solution manuals should not leak into ordinary problem discovery.
        for key in ([slug] if slug else records()):
            for s in sources(key):
                if s.get('role')=='answer_key':
                    clauses.append('NOT (p.vault=? AND p.source_id=?)');params.extend([key,s['id']])
    tail=(' AND '+' AND '.join(clauses)) if clauses else ''
    with connection() as db:
        def run(op):
            match=op.join('"'+w.replace('"','""')+'"' for w in words)
            return db.execute('SELECT p.vault,p.source_id,p.page,(SELECT b.title FROM books b WHERE b.vault=p.vault AND b.id=p.source_id) AS title,snippet(pages,3,\'⟦\',\'⟧\',\' … \',42) AS excerpt FROM pages p WHERE pages MATCH ?'+tail+' ORDER BY bm25(pages) LIMIT ?', [match,*params,max(1,min(limit,20))]).fetchall()
        rows=run(' AND ')
        if not rows:rows=run(' OR ')
        return [dict(r) for r in rows]

def sync_catalogue():
    raise ValueError('Configure/import a learner-specific catalogue explicitly; no author catalogue is bundled.')

def catalogue_search(query,limit=15):
    words=re.findall(r'\w+',query)[:10]
    if not words:raise ValueError('Supply title, author, topic or registry ID')
    with connection() as db:
        where=' AND '.join('(title || " " || authors || " " || topic || " " || registry_id) LIKE ?' for _ in words)
        rows=[dict(r) for r in db.execute('SELECT * FROM catalogue WHERE '+where+' LIMIT ?',[*['%'+w+'%' for w in words],max(1,min(limit,50))])]
    for r in rows:
        r['expected_pdf_exists']=(Path(r['target_directory'])/r['pdf_filename']).is_file()
    return rows

def views():
    master=[]
    for slug,rec in records().items():
        root=vault(slug);(root/'inbox').mkdir(mode=0o700,exist_ok=True)
        rows=sources(slug)
        changed=False
        for s in rows:
            if 'pdf_pages' not in s:
                with pymupdf.open(s['pdf']) as doc:s['pdf_pages']=len(doc)
                changed=True
        if changed:
            with lock():write_json(root/'.study/sources.json',rows)
        out=['# '+rec['name']+' — book registry','',
             'Download new study PDFs to `'+str(root/'inbox')+'`. Run `python study/manage.py attach; ask the tutor to import '+slug+'` or ask the tutor to import the inbox. The Study launcher also checks intake.',
             '', 'The original file stays put. Managed read-only copies live in `references/`; source IDs and physical PDF pages are stable. A registered book is not a completed reading assignment.','',
             '| Source ID | Title | Role | PDF pages |','|---|---|---|---|']
        for s in rows:
            role=s.get('role','existing reference')
            out.append('| `'+s['id']+'` | ['+s['title'].replace('|','/')+'](references/'+Path(s['pdf']).name+') | '+role+' | '+str(s['pdf_pages'])+' |')
            master.append({'vault':slug,**s})
        if not rows:out.append('| — | Current official documentation is in `library/` | documentation | — |')
        atomic(root/'REGISTRY.md','\n'.join(out)+'\n')
        cols=['id','title','role','pdf','original','source_url','pdf_pages','sha256','boundary_status']
        import io
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
        atomic(root/'REGISTRY.csv',stream.getvalue())
        home=root/'HOME.md';text=home.read_text();marker='## Library administration'
        if marker not in text:atomic(home,text+'\n'+marker+'\n\n[[REGISTRY]] lists actual books; download new PDFs to `inbox/`. [[library/STUDY-SYSTEM-GUIDE]] explains automatic intake, search and app handoffs.\n')
    write_json(CONTROL/'all-sources.json',master)
    return {'sources':len(master),'vaults':len(records())}

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    x=s.add_parser('import');x.add_argument('vault');x.add_argument('path');x.add_argument('--title');x.add_argument('--id');x.add_argument('--role',default='reference');x.add_argument('--url',default='')
    x=s.add_parser('intake');x.add_argument('vault',nargs='?')
    x=s.add_parser('index');x.add_argument('vault',nargs='?')
    x=s.add_parser('search');x.add_argument('query');x.add_argument('--vault');x.add_argument('--source');x.add_argument('--limit',type=int,default=8)
    x=s.add_parser('catalogue');x.add_argument('query');x.add_argument('--limit',type=int,default=15)
    s.add_parser('refresh')
    a=p.parse_args()
    if a.action=='import':
        result=import_pdf(a.vault,a.path,a.title,a.id,a.role,a.url);index(a.vault);views()
    elif a.action=='intake':
        result={k:intake(k) for k in ([a.vault] if a.vault else records())};index(a.vault);views()
    elif a.action=='index':result=index(a.vault)
    elif a.action=='search':result=search(a.query,a.vault,a.source,a.limit)
    elif a.action=='catalogue':result=catalogue_search(a.query,a.limit)
    else:result={'catalogue':sync_catalogue(),'views':views(),'index':index()}
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
