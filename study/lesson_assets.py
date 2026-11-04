"""Native editable diagrams with structural preflight and real export checks."""
import json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

def drawio(folder,title,nodes,edges):
    if not 1<=len(nodes)<=12 or len(edges)>20:raise ValueError('Use at most 12 readable concepts and 20 labelled relations')
    ids=[n['id'] for n in nodes]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate node ID')
    boxes=[]
    for n in nodes:
        if not n['label'].strip() or len(n['label'])>110:raise ValueError('Use concise concept labels')
        x,y,w,h=[n.get(k,d) for k,d in [('x',40),('y',100),('width',235),('height',90)]]
        if min(x,y)<0 or w<180 or h<70:raise ValueError('Unreadable node dimensions')
        for a,b,c,d in boxes:
            if x<a+c and a<x+w and y<b+d and b<y+h:raise ValueError('Overlapping concept nodes')
        boxes.append((x,y,w,h))
    for e in edges:
        if e['from'] not in ids or e['to'] not in ids or not e.get('label','').strip():raise ValueError('Each relation needs real endpoints and a meaningful label')
    mx=ET.Element('mxfile',host='app.diagrams.net');diagram=ET.SubElement(mx,'diagram',name='Lesson',id='lesson')
    model=ET.SubElement(diagram,'mxGraphModel',page='1',pageWidth='1040',pageHeight='760',background='#ffffff')
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    def cell(id,value,style,x,y,w,h):
        c=ET.SubElement(root,'mxCell',id=id,value=value,style=style,vertex='1',parent='1')
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    cell('heading',title,'text;html=0;align=left;fontSize=26;fontStyle=1;fontColor=#162D40;verticalAlign=middle;',40,12,950,65)
    for i,(n,box) in enumerate(zip(nodes,boxes)):
        cell(n['id'],n['label'],'rounded=1;whiteSpace=wrap;html=0;align=center;verticalAlign=middle;fontSize=18;spacing=12;fillColor='+n.get('color','#E9F4F2')+';strokeColor=#377D75;fontColor=#16342F;',*box)
    node_boxes=dict(zip(ids,boxes))
    routes=[]
    for i,e in enumerate(edges):
        x,y,w,h=node_boxes[e['from']];a,b,c,d=node_boxes[e['to']]
        points=[]
        if y==b and abs(x-a)<=350:
            ports='exitX=1;exitY=0.5;entryX=0;entryY=0.5;' if a>x else 'exitX=0;exitY=0.5;entryX=1;entryY=0.5;'
            route=[(x+w,y+h/2),(a,b+d/2)] if a>x else [(x,y+h/2),(a+c,b+d/2)]
        elif y!=b:
            downward=b>y
            corridor=(y+h+b)/2 if downward else (b+d+y)/2
            ports='exitX=0.5;exitY=1;entryX=0.5;entryY=0;' if downward else 'exitX=0.5;exitY=0;entryX=0.5;entryY=1;'
            points=[(x+w/2,corridor),(a+c/2,corridor)]
            route=[(x+w/2,y+h if downward else y),*points,(a+c/2,b if downward else b+d)]
        else:
            corridor=y+h+55
            ports='exitX=0.5;exitY=1;entryX=0.5;entryY=1;'
            points=[(x+w/2,corridor),(a+c/2,corridor)]
            route=[(x+w/2,y+h),*points,(a+c/2,b+d)]
        for (sx,sy),(tx,ty) in zip(route,route[1:]):
            for key,(nx,ny,nw,nh) in node_boxes.items():
                if key in {e['from'],e['to']}:continue
                if (sy==ty and ny<sy<ny+nh and max(min(sx,tx),nx)<min(max(sx,tx),nx+nw)) or (sx==tx and nx<sx<nx+nw and max(min(sy,ty),ny)<min(max(sy,ty),ny+nh)):
                    raise ValueError('An edge crosses an unrelated concept; revise the layout')
        routes.append(route)
        cell=ET.SubElement(root,'mxCell',id='edge'+str(i),value=e['label'],edge='1',parent='1',source=e['from'],target=e['to'],style='edgeStyle=none;'+ports+'rounded=0;html=0;endArrow=block;strokeColor=#455A70;fontColor=#273F55;fontSize=14;labelBackgroundColor=#ffffff;')
        geom=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
        if points:
            array=ET.SubElement(geom,'Array',attrib={'as':'points'})
            for px,py in points:ET.SubElement(array,'mxPoint',x=str(px),y=str(py))
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    native=folder/'concept.drawio';ET.ElementTree(mx).write(native,encoding='utf-8',xml_declaration=True)
    for fmt in ['svg','png']:
        run=subprocess.run([sys.executable,str(Path(__file__).with_name('drawio_headless.py')),'--export','--format',fmt,'--border','25','--output',str(folder/('concept.'+fmt)),str(native)],capture_output=True,text=True,timeout=55)
        if run.returncode:raise RuntimeError('Native Draw.io export failed: '+run.stderr[-350:])
    with Image.open(folder/'concept.png') as im:
        im.verify()
    with Image.open(folder/'concept.png') as im:size=list(im.size)
    svg=ET.parse(folder/'concept.svg').getroot()
    if not svg.tag.endswith('svg') or min(size)<150:raise ValueError('Invalid or empty diagram export')
    # Reopen the actual saved native document, not a detached in-memory graph.
    reopened=ET.parse(native);actual=reopened.findall('.//mxCell[@vertex="1"]')
    if len(actual)!=len(nodes)+1:raise ValueError('Native diagram did not retain its nodes')
    return {'native':str(native),'svg':str(folder/'concept.svg'),'png':str(folder/'concept.png'),
            'nodes':len(nodes),'edges':len(edges),'dimensions':size,'native_reopened':True,
            'content_review':'Structural/export checks only; inspect rendered labels and source claims before teaching.'}
