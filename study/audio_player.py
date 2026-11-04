"""Playable native HTML companion for an existing generated MP3/transcript."""
from pathlib import Path
import html
import mode_bridge
import study_settings

def publish(pipeline,items,audio_path,transcript_path,title):
 if not mode_bridge.selected(workspace_id=pipeline.workspace_id):return items
 from deeptutor.services.workspace import get_content_workspace_service
 service=get_content_workspace_service();binding=service.binding_by_id(pipeline.workspace_id)
 audio=next(i for i in items if i['filename']==audio_path.name)
 transcript=next(i for i in items if i['filename']==transcript_path.name)
 url=lambda item:html.escape(study_settings.origin()+item['url'],quote=True)
 target=audio_path.with_suffix('.html');heading=html.escape(title)
 document='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'''+heading+'''</title><style>
:root{color-scheme:light dark;--bg:#faf9f6;--fg:#24231f;--muted:#59574e;--line:#cbc8be;--accent:#12634e}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 system-ui,sans-serif}main{max-width:72ch;margin:auto;padding:clamp(18px,5vw,48px)}h1{font-size:clamp(25px,4vw,36px);line-height:1.2;letter-spacing:-.025em;text-wrap:balance}p{color:var(--muted)}audio{display:block;width:100%;margin:24px 0 14px}label{display:inline-flex;align-items:center;gap:10px}select{font:inherit;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}nav{display:flex;gap:12px 24px;flex-wrap:wrap;margin:20px 0 30px}a{color:var(--accent);text-underline-offset:4px}a:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:4px}details{border-top:1px solid var(--line);padding-top:20px}summary{cursor:pointer;font-weight:600}pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.75}#error{color:#9b2828}::selection{background:#bdddd0;color:#192c23}@media(prefers-color-scheme:dark){:root{--bg:#24231f;--fg:#f2f0e9;--muted:#c8c5b9;--line:#625f54;--accent:#9adbc0}#error{color:#ffb0aa}}
</style></head><body><main><h1>'''+heading+'''</h1><p>A source-linked conversation between a host and an expert. Listen, pause or read at your own pace.</p><audio id="audio" controls preload="metadata" aria-label="Audio lesson" src="'''+url(audio)+'''"></audio><label for="speed">Playback speed <select id="speed"><option value="0.75">0.75×</option><option value="1" selected>1×</option><option value="1.25">1.25×</option><option value="1.5">1.5×</option><option value="2">2×</option></select></label><p id="error" role="status" hidden>Audio could not load. Open the audio file below or reopen this lesson after the local service starts.</p><nav aria-label="Lesson files"><a href="'''+url(audio)+'''" download>Download audio</a><a href="'''+url(transcript)+'''" target="_blank" rel="noopener">Open transcript file</a></nav><details open><summary>Read the source-linked transcript</summary><pre>'''+html.escape(transcript_path.read_text())+'''</pre></details><p>This is a generated teaching overview, not evidence of independent understanding.</p></main><script>const audio=document.getElementById('audio');document.getElementById('speed').addEventListener('change',e=>audio.playbackRate=Number(e.target.value));audio.addEventListener('error',()=>document.getElementById('error').hidden=false);</script></body></html>'''
 target.write_text(document);target.chmod(0o600)
 published=service.publish(binding,[{'path':pipeline.workspace_logical_dir+'/'+target.name,'title':title,'caption':'Play audio and read transcript'}])
 return [*[item.to_dict() for item in published],*items]

def envelope(artifacts):
 """Use the existing native HTML renderer; file preview intentionally shows code."""
 if not mode_bridge.selected():return {}
 player=artifacts.audio_path.with_suffix('.html')
 if not player.exists():return {}
 return {'schema_version':'deeptutor.visualization/v1','render_type':'html',
         'renderer':{'id':'html','version':'1.0.0','target':'native','native_renderer':'html','entry_url':''},
         'payload':{'format':'text/html','data':player.read_text()},
         'presentation':{'title':artifacts.title,'description':'Play the audio lesson and read its source-linked transcript.','alt_text':'An audio player with playback speed, downloads, source-linked transcript and recovery instructions.','aspect_ratio':''},
         'interaction':{'events':[]},'fallback':{}}
