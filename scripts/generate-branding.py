#!/usr/bin/env python3
"""Regenerate approved owned literals and the complete icon family."""
import hashlib,io,json,re,sys,runpy
from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
import resvg_py
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
b=json.loads((ROOT/'branding/brand.json').read_text())
# BRANDING.json is the editable UI input; brand.json is the resolved manifest.
ui=json.loads((ROOT/'BRANDING.json').read_text())
for field in ('name','publisher'):
 value=ui[field]
 if not isinstance(value,str) or not value.strip() or len(value)>64 or re.search(r"[^\w .()&-]",value):
  raise SystemExit(f'Invalid branding {field}: use letters, numbers, spaces or .()&-')
logo=(ROOT/ui['logo']).resolve()
if not logo.is_relative_to(ROOT) or logo.suffix.lower()!='.svg' or not logo.is_file():
 raise SystemExit('logo must point to an SVG inside this repository')
svg=ET.fromstring(logo.read_text())
view_box=[float(v) for v in re.split(r'[ ,]+',svg.attrib.get('viewBox','').strip()) if v]
framing=ui.get('logo_framing',{})
if framing.get('source')==ui['logo']:view_box=framing['view_box']
if len(view_box)!=4 or view_box[2]<=0 or view_box[3]<=0:
 raise SystemExit('SVG requires a valid viewBox')
mode=ui.get('assistant_name_mode','brand')
if mode not in ('brand','customizable'):raise SystemExit('Invalid assistant_name_mode')
b['product'].update(display_name=ui['name'],short_name=ui['name'],description=ui.get('description','{name} AI workspace by {publisher}').format(name=ui['name'],publisher=ui['publisher']))
b['organization']['display_name']=ui['publisher']
b['assistant']['display_name']=ui['name']
b['assets'].update(source=ui['logo'],accessible_label=ui['name']+' logo',view_box=view_box)
b['ui']={'assistant_name_mode':mode}
b['ui']['revision']=hashlib.sha256((json.dumps(b,sort_keys=True)+logo.read_text()).encode()).hexdigest()[:12]
name=b['product']['display_name']
values={'@@PRODUCT@@':name,'@@PUBLISHER@@':b['organization']['display_name'],
        '@@LOGO_LABEL@@':b['assets']['accessible_label'],
        '@@DESCRIPTION@@':b['product']['description'],
        '@@EXPORT_PREFIX@@':b['distribution']['export_prefix'],
        '@@LOGO_PATH@@':b['assets']['logo'],
        '@@HELP_PATH@@':b['distribution']['documentation']}
def render(template):
 for key,value in values.items():template=template.replace(key,value)
 return template
# Catalog contains only application-owned source literals. Never process runtime
# messages, user content, provider output, databases, or uploaded documents.
catalog_path=ROOT/'branding/literals.json'
catalog=json.loads(catalog_path.read_text())
# Validate every slot before modifying any files.
for filename,entries in catalog.items():
 text=(ROOT/filename).read_text()
 if any(e['rendered'] not in text for e in entries):
  raise SystemExit(f'Branding slot changed in {filename}; review before regenerating')
for filename,entries in catalog.items():
 p=ROOT/filename;s=p.read_text()
 replacements={}
 for e in entries:
  if e['rendered'] not in s:
   raise SystemExit(f'Branding slot changed in {filename}; review upstream merge before regenerating')
  replacements[e['rendered']]=render(e['template'])
 if replacements:
  pattern='|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True))
  s=re.sub(pattern,lambda m:replacements[m.group()],s)
 for e in entries:e['rendered']=render(e['template'])
 p.write_text(s)
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
source=(ROOT/b['assets']['source']).read_text()
# Preserve paths/artwork; only frame the supplied source using the desktop crop.
source=source[source.index('<svg'):]
x,y,w,h=b['assets']['view_box']
framed=re.sub(r'viewBox="[^"]*"',f'viewBox="{x} {y} {w} {h}"',source,count=1)
(ROOT/b['assets']['logo']).write_text(framed)
# 20% inset keeps portrait inside the maskable safe circle, with opaque tile.
inner=re.sub(r'<svg\b[^>]*>','',framed,count=1).rsplit('</svg>',1)[0]
icon=f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><title>{escape(b["assets"]["accessible_label"])}</title><rect width="512" height="512" fill="#dedede"/><svg x="102.4" y="102.4" width="307.2" height="307.2" viewBox="{x} {y} {w} {h}">{inner}</svg></svg>'
for filename in ['favicon.svg','favicon-512.svg']:(ROOT/'static'/filename).write_text(icon)
for size in [16,32,180,192,512]:
 png=resvg_py.svg_to_bytes(svg_string=icon,width=size,height=size)
 filename='apple-touch-icon.png' if size==180 else f'favicon-{size}.png'
 (ROOT/'static'/filename).write_bytes(png)
Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=icon,width=256,height=256))).save(ROOT/'static/favicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
manifest=json.loads((ROOT/'static/manifest.json').read_text())
manifest.update(name=name,short_name=b['product']['short_name'],description=b['product']['description'])
manifest['shortcuts'][0]['description']=f'Open {name} ready for a new chat'
(ROOT/'static/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Metadata is present in the original HTML, before any JavaScript loads.
p=ROOT/'static/index.html';text=p.read_text()
for key,value in [('description',b['product']['description']),('author',b['organization']['display_name'])]:
 tag=f'<meta name="{key}" content="{escape(value, {chr(34): "&quot;"})}">'
 pattern=rf'<meta name="{key}"[^>]*>'
 text=re.sub(pattern,lambda _:tag,text) if re.search(pattern,text) else text.replace('</head>',tag+'\n</head>',1)
p.write_text(text)
# Change only the shell cache namespace; user storage keys and data stay intact.
p=ROOT/'static/sw.js';s=p.read_text()
digest=hashlib.sha256((json.dumps(b,sort_keys=True)+source).encode()).hexdigest()[:12]
s=re.sub(r"const CACHE_NAME = '[^']+';",f"const CACHE_NAME = 'altur-shell-{digest}-__WEBUI_VERSION__';",s)
p.write_text(s)
# Runtime packaging is scoped to this checkout's private copy. A source-only
# distribution can regenerate assets before running the documented setup.
(ROOT/'branding/brand.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
locale_helper=ROOT/'branding/runtime_locales.py'
if locale_helper.is_file():
 runpy.run_path(str(locale_helper))['generate_runtime_locales'](project=ROOT)
private_runtime=ROOT/'.runtime/hermes-agent'
if private_runtime.exists():
 sys.path.insert(0,str(ROOT))
 from branding.runtime import apply_runtime_branding
 apply_runtime_branding(private_runtime)
(ROOT/'static/branding.js').write_text('window.__ALTUR_BRAND__ = '+json.dumps({'name':name,'logo':b['assets']['logo'],'logo_label':b['assets']['accessible_label'],'assistant_name_mode':mode,'revision':b['ui']['revision']}).replace('<','\\u003c')+';\n')
print(f'Generated {name} literals, SVG/PNG/ICO assets and shell cache {digest}')
