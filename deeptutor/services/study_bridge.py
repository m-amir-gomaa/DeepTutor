"""Local study integration: maintained outside the installed distribution."""
from pathlib import Path
import sys
import os
_INSTALL=Path(os.environ.get('DEEPTUTOR_STUDY_LAYER',Path(__file__).resolve().parents[2]/'study'))
def implementation():
    path=str(_INSTALL)
    if path not in sys.path:sys.path.append(path)
    import mode_bridge
    return mode_bridge
async def prepare(context,capability):return await implementation().prepare(context,capability)
def retrieve(query,kb_name):return implementation().retrieve(query,kb_name)
def known_kb(kb_name):return implementation().known_kb(kb_name)
def speech_override():return implementation().speech_override()
def validate_html(payload):return implementation().validate_html(payload)
def cli_env(app_id,workspace_id=None):return implementation().cli_env(app_id,workspace_id)
def execution_env(workspace_id=None):return implementation().execution_env(workspace_id)
def publish_audio_player(pipeline,items,audio_path,transcript_path,title):
    implementation()
    import audio_player
    return audio_player.publish(pipeline,items,audio_path,transcript_path,title)
def audio_envelope(artifacts):
    implementation()
    import audio_player
    return audio_player.envelope(artifacts)
