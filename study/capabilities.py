"""Configured tools plus an optional private capability catalogue; no author paths."""
import json,re
import study_settings
from library import CONTROL
def search(query,limit=12):
 words=re.findall(r'\w+',query.casefold());limit=max(1,min(limit,40));path=CONTROL/'capabilities.json'
 if path.exists():
  scored=[]
  for row in json.loads(path.read_text()).get('entries',[]):
   name=row.get('name','').casefold();text=' '.join(str(v) for v in row.values()).casefold()
   if all(w in text for w in words):scored.append((sum(10 if w in name else 1 for w in words),{k:v for k,v in row.items() if k!='search_text'}))
  return [r for _,r in sorted(scored,key=lambda x:-x[0])[:limit]]
 rows=[]
 for name in ['python3','manim','ffmpeg','drawio','inkscape','node','bwrap','mineru-kit','mmdc']:
  path=study_settings.tool(name)
  if all(w in name.casefold() for w in words):rows.append({'name':name,'path':path,'state':'executable discovered; operation not verified' if path else 'not installed'})
 return rows[:limit]
