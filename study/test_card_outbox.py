"""Card delivery failures in an isolated vault; no real card or rating changes."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import asynccontextmanager
from mcp import types
import library,cards

class CardOutboxAcceptance(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='study-cards-test-');self.root=Path(self.temp.name)
  self.saved=library.BASE,library.CONTROL,cards.CONTROL
  library.BASE=self.root;library.CONTROL=self.root/'.control';cards.CONTROL=library.CONTROL
  library.CONTROL.mkdir();(self.root/'test/.study').mkdir(parents=True)
  (library.CONTROL/'vaults.json').write_text(json.dumps({'test':{'name':'Fixture','path':str(self.root/'test')}}))
  (library.CONTROL/'anki-local-key').write_text('temporary-fixture-value')
  self.fields={'Prompt':'What is the fixture target?','Answer':'One clear retrieval target.','Why':'This is a test fixture.','Source':'Generated acceptance fixture; no learner evidence.','Track':'Fixture','Key':'temporary-fixture-card'}
 def tearDown(self):
  library.BASE,library.CONTROL,cards.CONTROL=self.saved;self.temp.cleanup()
 async def test_stable_key_retry_does_not_duplicate(self):
  cards.queue('test',[self.fields]);cards.queue('test',[self.fields])
  with cards.database('test') as db:self.assertEqual(db.execute('SELECT count(*) FROM card_outbox').fetchone()[0],1)
  with self.assertRaises(ValueError):cards.queue('test',[{**self.fields,'Answer':'Conflicting content'}])
 async def test_executable_or_rating_fields_rejected(self):
  for fields in [{**self.fields,'Answer':'<img onerror="bad()">'},{**self.fields,'rating':'good'}]:
   with self.assertRaises(ValueError):cards.queue('test',[fields])
 async def test_interrupted_add_reconciles_without_second_add(self):
  cards.queue('test',[self.fields]);owner=self;remote={'exists':False,'adds':0}
  class Session:
   async def __aenter__(self):return self
   async def __aexit__(self,*args):pass
   async def initialize(self):pass
   async def call_tool(self,name,args):
    if name=='find_notes':payload={'noteIds':[123] if remote['exists'] else []}
    elif name=='notes_info':payload={'notes':[{'noteId':123,'fields':{k:{'value':v} for k,v in owner.fields.items()}}]}
    elif name=='add_note':
     remote['exists']=True;remote['adds']+=1;raise TimeoutError('Response interrupted after remote commit')
    else:raise AssertionError('No rating/deletion/review call allowed: '+name)
    return types.CallToolResult(content=[types.TextContent(type='text',text=json.dumps(payload))])
  @asynccontextmanager
  async def transport(*args,**kwargs):yield None,None,None
  with patch.object(cards,'streamablehttp_client',transport),patch.object(cards,'ClientSession',lambda *args:Session()):
   first=await cards.flush('test');self.assertIn('pending',first['outcomes'][0]['status'])
   second=await cards.flush('test');self.assertEqual(second['outcomes'][0]['status'],'already present')
  self.assertEqual(remote['adds'],1);self.assertFalse(second['ratings_changed'])

if __name__=='__main__':unittest.main()
