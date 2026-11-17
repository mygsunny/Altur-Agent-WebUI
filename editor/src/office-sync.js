import JSZip from 'jszip';
import * as exchange from './exchange.js';

const unsupported=detail=>{throw Error('Unsupported Office/native feature: '+detail+'; original retained');};
function xml(text){
 if(/<!DOCTYPE|<!ENTITY/i.test(text))unsupported('DTD');
 const doc=new DOMParser().parseFromString(text,'application/xml');
 if(doc.getElementsByTagName('parsererror').length)unsupported('malformed XML');
 return doc;
}
function canonical(text){
 const walk=n=>{
  if(n.nodeType===1){
   const attrs=Array.from(n.attributes).filter(a=>a.namespaceURI!=='http://www.w3.org/2000/xmlns/').map(a=>[a.namespaceURI||'',a.localName,a.value]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
   // Creation/modification timestamps are explicitly not working-document data.
   const volatile=n.namespaceURI==='http://purl.org/dc/terms/'&&['created','modified'].includes(n.localName);
   if(volatile&&Array.from(n.childNodes).some(c=>c.nodeType!==3))unsupported('timestamp structure');
   return [n.namespaceURI||'',n.localName,attrs,volatile?[]:Array.from(n.childNodes).map(walk).filter(v=>v!==null)];
  }
  if(n.nodeType===9)return Array.from(n.childNodes).map(walk).filter(v=>v!==null);
  if(n.nodeType===3||n.nodeType===4)return n.data;
  if(n.nodeType===8)return ['comment',n.data];
  if(n.nodeType===7)return ['pi',n.nodeName,n.nodeValue];
  return null;
 };
 return JSON.stringify(walk(xml(text)));
}
async function samePackage(bytes,reference){
 const a=await JSZip.loadAsync(bytes),b=await JSZip.loadAsync(reference);
 const names=z=>Object.keys(z.files).filter(n=>!z.files[n].dir).sort();
 if(JSON.stringify(names(a))!==JSON.stringify(names(b)))unsupported('package parts');
 for(const name of names(a)){
  const left=await a.file(name).async('string'),right=await b.file(name).async('string');
  if(canonical(left)!==canonical(right))unsupported(name);
 }
}
// Fail closed on the whole package, including attributes, relationships,
// workbook metadata and layout; an element-name denylist is not a schema.
export async function decodeOffice(bytes,kind){
 if(kind==='sheet'){
  const snapshot=await exchange.xlsxToSheet(bytes);
  await samePackage(bytes,await exchange.sheetToXlsx(snapshot));
  return snapshot;
 }
 if(kind!=='document')unsupported('kind');
 const zip=await JSZip.loadAsync(bytes),part=zip.file('word/document.xml');if(!part)unsupported('document');
 const doc=xml(await part.async('string')),body=doc.getElementsByTagNameNS('*','body')[0];if(!body)unsupported('body');
 const snapshot={type:'doc',content:[]};
 for(const p of Array.from(body.childNodes).filter(n=>n.nodeType===1&&n.localName==='p')){
  const content=[];
  const collect=n=>{if(n.nodeType!==1)return;if(n.localName==='t')content.push({type:'text',text:n.textContent});else if(n.localName==='br')content.push({type:'hardBreak'});else for(const c of Array.from(n.childNodes))collect(c);};collect(p);
  snapshot.content.push({type:'paragraph',...(content.length?{content}: {})});
 }
 await samePackage(bytes,await exchange.documentToDocx(snapshot));
 return snapshot;
}
const keys=(obj,allowed)=>{if(!obj||typeof obj!=='object'||Array.isArray(obj)||Object.keys(obj).some(k=>!allowed.includes(k)))unsupported('unknown schema field');};
const stable=value=>JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
const defaults=(obj,values)=>{for(const [k,v] of Object.entries(values))if(k in obj&&stable(obj[k])!==stable(v))unsupported(k);};
export async function encodeOffice(snapshot,kind){
 if(kind==='sheet'){
  keys(snapshot,['id','name','appVersion','locale','styles','sheetOrder','sheets','resources','calculationSettings']);
  defaults(snapshot,{calculationSettings:{iterativeCalculation:false,maxIterations:100,maxChange:0.001}});
  // Ordinary native keyboard commits carry an explicit RGB font color.
  // Preserve that narrow style in XLSX; all other formatting remains refused.
  if(snapshot.styles){keys(snapshot.styles,Object.keys(snapshot.styles));for(const style of Object.values(snapshot.styles)){keys(style,['cl']);keys(style.cl,['rgb']);if(!/^#[0-9a-fA-F]{6}$/.test(style.cl.rgb))unsupported('font color');}}
  const emptyResources={SHEET_RANGE_PROTECTION_PLUGIN:'',SHEET_AuthzIoMockService_PLUGIN:'{}',SHEET_WORKSHEET_PROTECTION_PLUGIN:'{}',SHEET_WORKSHEET_PROTECTION_POINT_PLUGIN:'{}',SHEET_DEFINED_NAME_PLUGIN:'',SHEET_RANGE_THEME_MODEL_PLUGIN:'{}'};
  if(snapshot.resources&&!Array.isArray(snapshot.resources))unsupported('resources');
  for(const r of snapshot.resources||[]){keys(r,['name','data']);if(!(r.name in emptyResources)||r.data!==emptyResources[r.name])unsupported('resource '+r.name);}
  if(!Array.isArray(snapshot.sheetOrder)||new Set(snapshot.sheetOrder).size!==snapshot.sheetOrder.length||snapshot.sheetOrder.length!==Object.keys(snapshot.sheets||{}).length)unsupported('sheet order');
  for(const id of snapshot.sheetOrder){
   const s=snapshot.sheets[id];
   keys(s,['id','name','rowCount','columnCount','cellData','hidden','mergeData','rowData','columnData','freeze','defaultRowHeight','defaultColumnWidth','rowHeader','columnHeader','showGridlines','zoomRatio','scrollTop','scrollLeft','rightToLeft','tabColor','status']);
   defaults(s,{hidden:0,mergeData:[],rowData:{},columnData:{},freeze:{startRow:-1,startColumn:-1,ySplit:0,xSplit:0},defaultRowHeight:24,defaultColumnWidth:88,rowHeader:{width:46,hidden:0},columnHeader:{height:20,hidden:0},showGridlines:1,zoomRatio:1,scrollTop:0,scrollLeft:0,rightToLeft:0,tabColor:'',status:1});
   if(s.id!==id||s.rowCount!==1000||s.columnCount!==100||typeof s.name!=='string')unsupported('sheet dimensions/identity');
   for(const [r,row] of Object.entries(s.cellData||{})){
    if(!/^(0|[1-9][0-9]*)$/.test(r)||+r>=1000)unsupported('row bounds');
    for(const [c,cell] of Object.entries(row)){
     if(!/^(0|[1-9][0-9]*)$/.test(c)||+c>=100)unsupported('column bounds');
     keys(cell,['v','f','t','s']);
     if(cell.s!==undefined&&(typeof cell.s!=='string'||!Object.hasOwn(snapshot.styles||{},cell.s)))unsupported('cell style');
     if(cell.v!==null&&cell.v!==undefined&&!['number','boolean','string'].includes(typeof cell.v))unsupported('cell value');
     if(typeof cell.v==='number'&&!Number.isFinite(cell.v))unsupported('nonfinite cell');
     if(cell.f!==undefined&&(typeof cell.f!=='string'||!cell.f.startsWith('=')))unsupported('formula');
     if(cell.t!==undefined&&cell.t!==({string:1,number:2,boolean:3}[typeof cell.v]))unsupported('cell type');
    }
   }
  }
 }else if(kind==='document'){
  const walk=node=>{
   keys(node,['type','content','text','marks','attrs']);
   if(!['doc','paragraph','text','hardBreak'].includes(node.type)||node.marks?.length||Object.keys(node.attrs||{}).length)unsupported('document formatting/attributes');
   if(!['text'].includes(node.type)&&node.text!==undefined)unsupported('unexpected text field');
   if(node.type==='text'&&(typeof node.text!=='string'||node.content))unsupported('text');
   if(node.type==='hardBreak'&&(node.content||node.text))unsupported('break');
   if(node.content&&!Array.isArray(node.content))unsupported('content');
   for(const child of node.content||[]){if(node.type==='doc'?child.type!=='paragraph':!['text','hardBreak'].includes(child.type))unsupported('document structure');walk(child);}
  };walk(snapshot);if(snapshot.type!=='doc')unsupported('document root');
 }else unsupported('kind');
 return kind==='sheet'?exchange.sheetToXlsx(snapshot):exchange.documentToDocx(snapshot);
}
const b64=bytes=>{let value='';for(const byte of new Uint8Array(bytes))value+=String.fromCharCode(byte);return btoa(value);};
const fingerprint=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),b=>b.toString(16).padStart(2,'0')).join('');
export function installOfficeSync({api,current,reload,report}){
 let busy=false,session,pending,dead=false;
 const status=document.createElement('span'),button=document.createElement('button');button.textContent='Import external Office version';button.hidden=true;
 document.getElementById('save-status').after(status,button);
 const show=text=>{status.textContent=' · Office: '+text;};
 const valid=s=>{const c=current();return !dead&&c&&c.id===s.id&&c.generation===s.generation;};
 function bind(c){
  if(!session||session.id!==c.id||session.generation!==c.generation){session=Object.freeze({id:c.id,generation:c.generation,kind:c.kind});pending=undefined;button.hidden=true;}
  return session;
 }
 async function acknowledge(s,p){
  const receipt=await api('sync',{action:'accept',document_id:s.id,hash:p.hash,offer_id:p.offer_id,native_hash:p.native_hash});
  if(receipt.state!=='synced'||(receipt.hash&&receipt.hash!==p.hash))throw Error('Office acknowledgment unavailable');
  if(!valid(s)||pending!==p)return;
  pending=undefined;button.hidden=true;show('imported; Undo reset');
 }
 async function importPending(){
  if(busy||!pending)return;const c=current(),s=session,p=pending;
  if(!valid(s)||!c.ready)return;
  busy=true;
  try{
   if(p.committed){await acknowledge(s,p);return;}
   if(c.dirty&&!confirm('Preserve local native snapshot, then replace with external Office version? Undo history resets.'))return;
   // The reload owns a captured adapter generation, including every save await.
   const result=await reload(p.snapshot,s,p.hash,p.offer_id);
   if(!valid(s)||pending!==p)return;
   p.committed=true;p.native_hash=result?.native_hash||await fingerprint(JSON.stringify(current().snapshot));
   if(!valid(s))return;
   await acknowledge(s,p);
  }catch(e){if(valid(s))show('import reconciliation pending: '+e.message);}finally{busy=false;}
 }
 button.onclick=importPending;
 async function tick(){
  if(busy||dead)return;const c=current();if(!c?.ready)return;
  const s=bind(c);
  if(pending?.committed){busy=true;try{await acknowledge(s,pending);}catch(e){if(valid(s))show('acknowledgment pending: '+e.message);}finally{busy=false;}return;}
  if(pending)return;
  busy=true;
  try{
   const r=await api('sync',{action:'poll',document_id:s.id});if(!valid(s))return;
   if(['disabled','offline','settling'].includes(r.state)){show(r.state);return;}
   if(r.state==='external'){
    const bytes=Uint8Array.from(atob(r.bytes),x=>x.charCodeAt(0));
    const snapshot=await decodeOffice(bytes,s.kind);if(!valid(s))return;
    pending={snapshot,hash:r.hash,offer_id:r.offer_id};
    // Explicit choice: do not silently reset native Undo even if autosaved.
    button.hidden=false;show('external version available — both copies retained');return;
   }
   const json=JSON.stringify(c.snapshot),hash=await fingerprint(json);if(!valid(s))return;
   if(r.state==='unbound'||(r.native_hash&&hash!==r.native_hash)){
    const bytes=await encodeOffice(c.snapshot,s.kind);
    if(!valid(s)||!current().ready||JSON.stringify(current().snapshot)!==json)return;
    const result=await api('sync',{action:'publish',document_id:s.id,extension:s.kind==='sheet'?'xlsx':'docx',base:r.hash??null,bytes:b64(bytes),native_hash:hash});
    if(valid(s))show('published '+result.filename+' (original unchanged)');
   }else show('latest output '+(r.filename||'unavailable')+'; originals never overwritten');
  }catch(e){if(valid(s)){show('paused/offline: '+e.message);report('Office sync: '+e.message);}}finally{busy=false;}
 }
 const timer=setInterval(tick,2500);return {tick,destroy(){dead=true;clearInterval(timer);status.remove();button.remove();}};
}
