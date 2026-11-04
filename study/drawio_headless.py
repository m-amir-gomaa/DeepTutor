#!/usr/bin/env python3
"""Run the real pinned Draw.io exporter in its own authenticated X display."""
import subprocess,sys,tempfile,os,shutil
from pathlib import Path
import study_settings

safe_path=os.pathsep.join(p for p in os.environ.get('PATH','').split(os.pathsep)
                          if Path(p).resolve()!=Path(__file__).parent/'bin')
native=study_settings.load()['tools'].get('drawio') or shutil.which('drawio',path=safe_path)
if not native:raise SystemExit('Configure/install the native Draw.io executable; the study wrapper is not the renderer.')

with tempfile.TemporaryDirectory(prefix='study-drawio-') as folder:
    command=[study_settings.tool('xvfb-run','xvfb-run'),'--auto-servernum',
             '--server-args=-screen 0 1280x900x24 -nolisten tcp',
             native,
             '--user-data-dir='+str(Path(folder)/'profile'),*sys.argv[1:]]
    raise SystemExit(subprocess.call(command))
