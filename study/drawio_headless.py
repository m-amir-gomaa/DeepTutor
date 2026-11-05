#!/usr/bin/env python3
"""Run the native Draw.io exporter with a private temporary profile."""
import subprocess,sys,tempfile,os,shutil
from pathlib import Path
import study_settings

def export_command(arguments, profile, system=None):
    import platform
    system=system or platform.system()
    safe_path=os.pathsep.join(p for p in os.environ.get('PATH','').split(os.pathsep)
                              if Path(p).resolve()!=Path(__file__).parent/'bin')
    native=study_settings.load()['tools'].get('drawio') or shutil.which('drawio',path=safe_path)
    if not native and system=='Darwin':
        native=next((str(p) for p in [Path('/Applications/draw.io.app/Contents/MacOS/draw.io'),
                    Path.home()/'Applications/draw.io.app/Contents/MacOS/draw.io'] if p.is_file()),None)
    if not native:raise RuntimeError('Configure/install native Draw.io; the study wrapper is not the renderer.')
    command=[native,'--user-data-dir='+str(profile),*arguments]
    if system=='Linux':
        xvfb=study_settings.tool('xvfb-run')
        if not xvfb:raise RuntimeError('Install/configure xvfb-run for the Linux Draw.io exporter.')
        command=[xvfb,'--auto-servernum','--server-args=-screen 0 1280x900x24 -nolisten tcp',*command]
    elif system!='Darwin':raise RuntimeError('Use the study exporter on macOS or Linux/WSL2.')
    return command

def main():
    with tempfile.TemporaryDirectory(prefix='study-drawio-') as folder:
        raise SystemExit(subprocess.call(export_command(sys.argv[1:],Path(folder)/'profile')))

if __name__=='__main__':main()
