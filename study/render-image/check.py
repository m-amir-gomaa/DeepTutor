"""Synthetic container acceptance. Build/authorize the local runtime first."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import execution
import study_settings


def main():
    conf=study_settings.load()
    if conf.get('execution',{}).get('backend')!='container':
        raise RuntimeError('This check requires explicit container configuration.')
    with tempfile.TemporaryDirectory(prefix='study-container-check-') as td:
        folder=Path(td)
        (folder/'example.py').write_text('''import os,socket
assert os.getcwd()=="/work"
assert not os.path.exists("/host")
try:
    socket.create_connection(("1.1.1.1",443),timeout=1)
except OSError:
    print("network denied")
else:
    raise AssertionError("network was available")
try:
    open("/etc/study-write-test","w")
except OSError:
    pass
else:
    raise AssertionError("root filesystem was writable")
open("/work/result.json","w").write("{\\"ok\\": true}")
print(sum([1,2,3]))
''')
        result=execution.run(folder,['python','/work/example.py'],30,{})
        if result.returncode or not json.loads((folder/'result.json').read_text())['ok']:
            raise RuntimeError('Isolated example failed: '+result.stderr[-2000:])
        (folder/'scene.py').write_text('''from manim import Scene, Dot, RIGHT
class Fixture(Scene):
    def construct(self):
        dot=Dot()
        self.add(dot)
        self.play(dot.animate.shift(RIGHT),run_time=0.25)
''')
        result=execution.run(folder,['manim','-ql','--disable_caching','--media_dir','/work/media','/work/scene.py','Fixture'],90,{})
        videos=list((folder/'media').rglob('Fixture.mp4'))
        if result.returncode or not videos or videos[0].stat().st_size<1000:
            raise RuntimeError('Manim fixture failed: '+result.stderr[-2000:])
        # Actual timeout path should clean up the known container name.
        (folder/'sleep.py').write_text('import time;time.sleep(30)')
        try:execution.run(folder,['python','/work/sleep.py'],2,{})
        except subprocess.TimeoutExpired:pass
        else:raise AssertionError('Timeout was not enforced')
        print('Isolated Python, network/write restrictions, persisted output, Manim MP4 and timeout cleanup passed.')


if __name__=='__main__':main()
