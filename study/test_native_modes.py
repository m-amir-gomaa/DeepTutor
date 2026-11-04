"""Protocol and browser failures that blocked real study modes."""
import asyncio
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import httpx
from deeptutor.services.llm.provider_core.openai_codex_provider import OpenAICodexProvider,_request_codex
from deeptutor.services.llm.provider_core.base import LLMResponse
from deeptutor.runtime.agentic.client import _provider_streams_tool_args

class NativeModes(unittest.IsolatedAsyncioTestCase):
 async def test_mcp_error_flag_reaches_native_tool_result(self):
  from types import SimpleNamespace
  from mcp import types
  from deeptutor.services.mcp.manager import MCPConnectionManager,MCPToolAdapter
  class Session:
   async def call_tool(self,*args,**kwargs):return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text='The requested source is unavailable.')])
  text=await MCPConnectionManager._call_once(SimpleNamespace(session=Session()),'lookup',{},3)
  self.assertFalse(text.success)
  class Manager:
   async def call_tool(self,*args,**kwargs):return text
  adapter=MCPToolAdapter(manager=Manager(),server_name='fixture',original_name='lookup',description='Fixture',input_schema={},tool_timeout=3)
  result=await adapter.execute();self.assertFalse(result.success);self.assertIn('unavailable',result.content)

 async def test_research_report_requests_supported_effort(self):
  from deeptutor.agents.research.pipeline import ResearchPipeline,_PROTOCOL_REPORT_INTRO
  pipeline=ResearchPipeline.__new__(ResearchPipeline)
  pipeline.model='gpt-6.1-sol';pipeline.language='en'
  pipeline._build_system_user_messages=lambda *args:[]
  pipeline._build_simple_trace_meta=lambda **kwargs:{}
  captured={}
  async def step(**kwargs):captured.update(kwargs);raise asyncio.CancelledError()
  pipeline._run_labeled_step=step
  with self.assertRaises(asyncio.CancelledError):
   await pipeline._stream_report_step(system_prompt='Write introduction',user_prompt='Existing evidence',protocol=_PROTOCOL_REPORT_INTRO,stream=None,client=None,label='Intro',call_id_root='test',max_tokens=1000)
  self.assertEqual(captured['reasoning_effort'],'low')

 async def test_codex_forwards_live_tool_preview(self):
  provider=OpenAICodexProvider();seen={}
  async def call(*args,**kwargs):seen.update(kwargs);return LLMResponse(content='')
  async def preview(*args):pass
  provider._call_codex=call
  self.assertTrue(_provider_streams_tool_args(provider))
  await provider.chat_stream([],on_tool_args_delta=preview)
  self.assertIs(seen['on_tool_args_delta'],preview)

 async def test_sse_previews_arrive_before_one_complete_call(self):
  item={'id':'item-test','call_id':'call-test','type':'function_call','name':'submit_visualization','arguments':''}
  events=[{'type':'response.output_item.added','item':item},
   {'type':'response.function_call_arguments.delta','item_id':'item-test','delta':'{"payload":'},
   {'type':'response.function_call_arguments.delta','item_id':'item-test','delta':'"complete"}'},
   {'type':'response.output_item.done','item':{**item,'arguments':'{"payload":"complete"}'}},
   {'type':'response.completed','response':{'status':'completed'}}]
  previews=[];finished=False
  class Stream(httpx.AsyncByteStream):
   async def __aiter__(self):
    nonlocal finished
    for event in events:
     await asyncio.sleep(.01)
     yield ('data: '+json.dumps(event)+'\n\n').encode()
    finished=True
  async def handler(request):return httpx.Response(200,stream=Stream())
  real=httpx.AsyncClient
  async def preview(*args):previews.append((args,finished))
  with patch('deeptutor.services.llm.provider_core.openai_codex_provider.httpx.AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler))):
   text,calls,reason=await _request_codex('https://example.invalid/responses',{}, {},True,on_tool_args_delta=preview)
  self.assertEqual(len(previews),2);self.assertTrue(all(not x[1] for x in previews))
  self.assertEqual(len(calls),1);self.assertEqual(calls[0].arguments,{'payload':'complete'})

class BrowserValidation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.good='''<!doctype html><html><head><meta name="viewport" content="width=device-width"></head><body><h1>A complete source-grounded demonstration</h1><p id="state">The first state explains what changes.</p><button onclick="document.getElementById('state').textContent='The second state has changed.'">Next</button><button onclick="document.getElementById('state').textContent='The first state explains what changes.'">Reset</button><script>const ready=true;</script></body></html>'''
 def check(self,html):
  import os,study_settings
  env={**os.environ,'STUDY_CHROMIUM':study_settings.tool('chromium',''),
       'STUDY_PLAYWRIGHT_MODULE':study_settings.tool('playwright-module','playwright')}
  result=subprocess.run(['node',str(Path(__file__).with_name('validate_html.cjs'))],input=json.dumps({'html':html}),capture_output=True,text=True,timeout=35,env=env)
  return json.loads(result.stdout)
 def test_working_controls(self):self.assertTrue(self.check(self.good)['ok'])
 def test_script_error_rejected(self):self.assertFalse(self.check(self.good.replace('const ready=true;','throw new Error("broken lesson");'))['ok'])
 def test_inert_controls_rejected(self):self.assertFalse(self.check(self.good.replace("document.getElementById('state').textContent='The second state has changed.'",'void 0'))['ok'])
 def test_external_dependency_rejected(self):self.assertFalse(self.check(self.good.replace('</body>','<img src="https://example.invalid/image.png"></body>'))['ok'])
 def test_inert_secondary_button_rejected(self):
  result=self.check(self.good.replace('<button onclick=', '<button type="button">Broken secondary action</button><button onclick=',1))
  self.assertFalse(result['ok']);self.assertTrue(any('Broken secondary action' in e for e in result['errors']))
 def test_range_select_checkbox_without_forward_button(self):
  html='''<!doctype html><html><head><meta name="viewport" content="width=device-width"></head><body><h1>Explore a biological concentration model</h1><p>Change concentration, choose a model, and compare the visible prediction. Values are illustrative, not measured biology.</p><label>Concentration <input id="c" type="range" min="0" max="10" value="2"></label><label>Model <select id="m"><option>Linear</option><option>Saturating</option></select></label><label><input type="checkbox" id="compare"> Compare prediction</label><output id="prediction">2 Linear false</output><button id="reset">Reset</button><script>const c=document.getElementById('c'),m=document.getElementById('m'),compare=document.getElementById('compare'),out=document.getElementById('prediction');function draw(){out.textContent=c.value+' '+m.value+' '+compare.checked}for(const el of [c,m,compare])el.addEventListener('input',draw);document.getElementById('reset').onclick=()=>{c.value=2;m.selectedIndex=0;compare.checked=false;draw()};</script></body></html>'''
  result=self.check(html);self.assertTrue(result['ok'],result['errors']);self.assertEqual(len(result['checks']),3)
  self.assertTrue(all(a['changed'] for a in result['actions'] if a['kind']!='return/reset'))
 def test_canvas_render_and_keyboard(self):
  html='''<!doctype html><html><head><meta name="viewport" content="width=device-width"></head><body><h1>Vector projection on an original canvas</h1><p>Switch between two computed vector positions. The arrow is an illustrative geometric example.</p><canvas id="plot" width="220" height="100" aria-label="Vector projection"></canvas><button id="next">Next vector</button><button id="reset">Reset</button><script>const ctx=document.getElementById('plot').getContext('2d');let n=0;function draw(){ctx.clearRect(0,0,220,100);ctx.fillStyle=n%2?'red':'blue';ctx.fillRect(20,30,n%2?150:60,12)}document.getElementById('next').onclick=()=>{n++;draw()};document.getElementById('reset').onclick=()=>{n=0;draw()};draw();</script></body></html>'''
  result=self.check(html);self.assertTrue(result['ok'],result['errors']);self.assertTrue(any(a['kind']=='keyboard Enter' and a['changed'] for a in result['actions']))
 def test_missing_head_rejected(self):
  result=self.check(self.good.replace('<head>','').replace('</head>',''));self.assertFalse(result['ok'])
 def test_reset_must_stop_animation_interval(self):
  html=self.good.replace("const ready=true;","let timer=null;document.querySelector('button').onclick=()=>{document.getElementById('state').textContent='Running';timer=setInterval(()=>{},1000)};")
  result=self.check(html);self.assertFalse(result['ok']);self.assertTrue(any('interval' in e for e in result['errors']))
 def test_broken_accessible_reference_rejected(self):
  result=self.check(self.good.replace('>Next</button>',' aria-labelledby="missing"></button>'));self.assertFalse(result['ok'])

if __name__=='__main__':unittest.main()
