"""Real Inkscape rendering for the installed CLI-Anything project format."""
from pathlib import Path
import os
import struct
import subprocess
import tempfile

import study_settings
INKSCAPE=study_settings.tool('inkscape','inkscape')

def render(project,output_path,format,overwrite=False,width=None,height=None,dpi=96,background=None):
 from cli_anything.inkscape.core.document import save_svg
 output=Path(output_path).resolve()
 if output.exists() and not overwrite:raise FileExistsError('Output already exists: '+str(output))
 output.parent.mkdir(parents=True,exist_ok=True)
 if not Path(INKSCAPE).exists():raise RuntimeError('The pinned native Inkscape renderer is missing.')
 with tempfile.TemporaryDirectory(prefix='.inkscape-render-',dir=output.parent) as tmp:
  svg=Path(tmp)/'source.svg';save_svg(project,str(svg))
  command=[INKSCAPE,str(svg),'--export-type='+format,'--export-filename='+str(output)]
  if format=='png':
   command+=['--export-dpi='+str(dpi)]
   if width:command+=['--export-width='+str(width)]
   if height:command+=['--export-height='+str(height)]
   if background:command+=['--export-background='+background,'--export-background-opacity=1']
  r=subprocess.run(command,capture_output=True,text=True,timeout=60)
  if r.returncode:raise RuntimeError('Native Inkscape export failed: '+r.stderr[-700:])
 if not output.is_file() or output.stat().st_size<30:raise RuntimeError('Native export did not produce the requested file.')
 magic=output.read_bytes()[:24]
 if format=='png' and magic[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('Native renderer returned a non-PNG file.')
 if format=='pdf' and not magic.startswith(b'%PDF-'):raise RuntimeError('Native renderer returned a non-PDF file.')
 result={'output':str(output),'format':format,'rendered_by':'Inkscape 1.4.4 native','size_bytes':output.stat().st_size}
 if format=='png':result.update(dict(zip(['width','height'],struct.unpack('>II',magic[16:24]))))
 return result
