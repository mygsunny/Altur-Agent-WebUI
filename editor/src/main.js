import {randomId,snapshotHash} from './browser-capabilities.js';
import {Controller} from './controller.js';
import {PhraseGate,AudioQueue} from './voice.js';
import {DocumentAdapter} from './document.js';
import './style.css';
const $=id=>document.getElementById(id), report=text=>{$('status').textContent=text};
if(!isSecureContext){$('listen').textContent='Voice requires HTTPS';$('voice-status').textContent='Microphone unavailable on plain HTTP LAN. Ask the operator for trusted HTTPS, then allow microphone access. Manual typing and Apply still work.';}
let csrf='',profile='',adapter,kind,id,revision=0,saved='',release,opening=false,saving=false,saveBlocked=false,owner='',leaseUntil=0;
let officePaused=true,connectionGrant,inferenceBusy=false;
function ensureLease(reconciling=false){if(saveBlocked||(!reconciling&&officePaused)||performance.now()>=leaseUntil){$('editor').inert=true;controller.stop();throw Error('Writable ownership paused; waiting for connection and Office reconciliation');}}
function pauseOffice(value,grant){const changed=value&&!officePaused;officePaused=value;connectionGrant=value?undefined:grant;$('editor').inert=value||opening||saveBlocked;if(changed){controller.stop();stopVoice();}for(const name of ['apply','undo','redo','listen'])$(name).disabled=value;}
let recordIdentity,officeGeneration=0,officeUploading=false;
const root=await fetch('/').then(r=>r.text()).catch(()=> '');
const token=root.match(/csrfToken:("(?:[^"\\]|\\.)*")/);if(token)csrf=JSON.parse(token[1]);
async function api(path,body,signal){
 const response=await fetch('/api/cowork/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Hermes-CSRF-Token':csrf}:{},body:body?JSON.stringify({owner,connection_grant:connectionGrant,...body,profile}):undefined,signal:signal||AbortSignal.timeout(8000)});
 if(response.status===401)throw Error('Sign in at the Chat page, then reload this editor and retry New document or Open.');
 const result=await response.json();if(!response.ok)throw Error((result.error||'Request failed')+(response.status===409?' — close other writable tabs, wait 30 seconds for their lease to expire, then retry Open.':''));return result;
}
const controller=new Controller((body,signal)=>api('intent',body,signal),report,busy=>{inferenceBusy=busy;$('apply').disabled=opening||officePaused;$('apply').textContent=busy?'Queue command':'Apply';$('apply').setAttribute('aria-busy',String(busy));},items=>{$('command-queue').replaceChildren(...items.slice(-12).map(item=>{const row=document.createElement('li');row.textContent=item.status+': '+item.text+(item.error?' — '+item.error:'');return row;}));});
window.cowork={controller,pauseVoice:stopVoice,get adapter(){return adapter},get kind(){return kind},get id(){return id}};
function stopVoice(session=recordIdentity){
 if(!session)return;
 session.discard=true;clearInterval(session.timer);session.queue?.close();
 if(session.recorder?.state==='recording')session.recorder.stop();
 session.media?.getTracks().forEach(t=>t.stop());
 const context=session.context;session.context=undefined;context?.close()?.catch(()=>{});
 // Late permission/resume/STT completions own only their resources.
 if(recordIdentity===session){recordIdentity=undefined;controller.stop();$('listen').textContent='Enable voice';}
}
async function save(duringOpen=false){
 if(!adapter||officePaused||(opening&&duringOpen!==true)||saving||saveBlocked)return;
 const snapshot=adapter.snapshot(),json=JSON.stringify(snapshot);if(json===saved)return;
 const active=id,activeAdapter=adapter; saving=true;
 try{const result=await api('document',{document_id:id,kind,revision,snapshot});
  if(active!==id||adapter!==activeAdapter)return;
  revision=result.document.revision;saved=json;$('save-status').textContent='Saved revision '+revision;
 }catch(e){if(active===id&&adapter===activeAdapter){pauseOffice(true);window.cowork.officeSync?.disconnect();report(e.message+' — local draft retained. Autosave paused for reconciliation.');}}
 finally{saving=false;}
}
async function open(nextKind,nextId,snapshot){
 if(opening)return;
 if(adapter&&nextId===id){report('Ready — '+kind+'. Existing editor and shared native Undo retained.');return;}
 opening=true;officeGeneration++;officePaused=true;
 let candidate,host,unlock;const previousProfile=profile;
 $('editor').inert=true;for(const name of ['new-doc','new-sheet','reopen','apply','undo','redo','listen'])$(name).disabled=true;
 try{
  nextId=nextId||randomId();
  stopVoice();controller.stop();
  if(adapter){if(JSON.stringify(adapter.snapshot())!==saved)await api('sync',{action:'preserve-draft',document_id:id,kind,snapshot:adapter.snapshot()});await save(true);if(saveBlocked)throw Error('Export local work and reload before switching: save is blocked');}
  if(saving)throw Error('Save still running; retry document switch');
  let loaded=await api('document?id='+encodeURIComponent(nextId));profile=loaded.profile;
  const acquired=await new Promise((resolve,reject)=>{
   // HTTP LAN has no Web Locks: server atomic leases arbitrate fresh per-open owners.
   // Never reuse sessionStorage ownership here (duplicated tabs clone it).
   if(!navigator.locks){resolve(true);return;}
   navigator.locks.request('altur-cowork:'+profile+':'+nextId,{ifAvailable:true},lock=>{
    if(!lock){resolve(false);return;}
    resolve(true);return new Promise(done=>{unlock=done});
   }).catch(reject);
  });
  if(!acquired)throw Error('This document already has a writable browser tab. Close it before opening here.');
  const ownerKey='cowork-owner:'+profile+':'+nextId;
  const nextOwner=(navigator.locks&&sessionStorage.getItem(ownerKey))||randomId();
  const claimStart=performance.now();
  try{
   await api('claim',{document_id:nextId,owner:nextOwner});
   const latest=await api('document?id='+encodeURIComponent(nextId));
   if(latest.profile!==profile)throw Error('Profile changed while opening document');
   loaded=latest;
  }catch(error){throw error;}
  if(loaded.document){nextKind=loaded.document.kind;snapshot=loaded.document.snapshot;}
  if(!['sheet','document'].includes(nextKind))throw Error('Invalid document kind');
  host=document.createElement('div');host.style.cssText='width:100%;height:100%';
  if(nextKind==='sheet'){const {SheetAdapter}=await import('./sheet.js');candidate=new SheetAdapter(host,snapshot);}
  else candidate=new DocumentAdapter(host,snapshot);
  candidate.snapshot();
  candidate?.api?.toggleDarkMode(document.documentElement.classList.contains('dark'));
  for(const name of ['apply','undo','redo']){const native=candidate[name].bind(candidate);candidate[name]=(...args)=>{ensureLease();return native(...args)};}
  sessionStorage.setItem(ownerKey,nextOwner);
  const oldAdapter=adapter,oldRelease=release;
  $('editor').replaceChildren(host);adapter=candidate;candidate=undefined;host=undefined;
  owner=nextOwner;leaseUntil=claimStart+25000;release=unlock;unlock=undefined;
  try{oldAdapter?.destroy();}finally{oldRelease?.();}
  $('editor').inert=false;
  id=nextId;kind=nextKind;revision=loaded.document?.revision||0;saved=loaded.document?JSON.stringify(snapshot):'';saveBlocked=false;
  $('identity').value=id;history.replaceState(null,'','?id='+encodeURIComponent(id));controller.open(id,adapter);localStorage.setItem('altur-cowork-last:'+profile,id);report('Ready — '+kind+'. Shared native Undo.');
 }catch(e){profile=previousProfile;try{candidate?.destroy();}finally{host?.replaceChildren();unlock?.();}report(e.message);}finally{opening=false;for(const name of ['new-doc','new-sheet','reopen'])$(name).disabled=false;pauseOffice(officePaused);}
}
$('new-doc').onclick=()=>open('document');$('new-sheet').onclick=()=>open('sheet');
$('reopen').onclick=()=>open('document',$('identity').value);
$('undo').onclick=()=>adapter?.undo();$('redo').onclick=()=>adapter?.redo();$('save').onclick=save;
$('stop').onclick=()=>{controller.stop();stopVoice()};$('pause').onclick=()=>{stopVoice();controller.stop();report('Voice paused; pending work canceled. Completed edits remain.');};
$('apply').onclick=()=>{if(adapter&&!opening){const text=$('request').value;if(controller.submit(text))$('request').value='';}};
$('request').onkeydown=e=>{if(e.key==='Enter')$('apply').click()};
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='z'&&!e.target.closest('#editor')){e.preventDefault();e.stopImmediatePropagation();e.shiftKey?adapter?.redo():adapter?.undo();}},true);
$('theme').onclick=()=>{const dark=document.documentElement.classList.toggle('dark');adapter?.api?.toggleDarkMode(dark);};
async function download(bytes,name,type){const blob=new Blob([bytes],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$('export').onclick=async()=>{
 try{
  if(!adapter)return;
  const format=prompt('Export format: native (full working snapshot) or office (limited XLSX/DOCX subset)','native');if(!format)return;
  if(format==='native')return download(JSON.stringify({kind,snapshot:adapter.snapshot()}),id+'.json','application/json');
  if(format!=='office')throw Error('Choose native or office');
  if(!confirm('Limited Office export: values/formulas only for spreadsheets; paragraph/heading/basic text marks/tables for documents. Layout, styles, comments, charts and tracked changes are not preserved. Continue?'))return;
  const x=await import('./exchange.js');await download(await(kind==='sheet'?x.sheetToXlsx(adapter.snapshot()):x.documentToDocx(adapter.snapshot())),id+(kind==='sheet'?'.xlsx':'.docx'),kind==='sheet'?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
 }catch(e){report(e.message)}
};
$('import').onchange=async e=>{
 if(officeUploading)return;officeUploading=true;const uploadGeneration=officeGeneration;
 try{
  const file=e.target.files[0];if(!file)return;if(file.size>8*1024*1024)throw Error('Import limit 8 MiB');
  const ext=file.name.split('.').pop().toLowerCase(),buffer=await file.arrayBuffer();
  if(ext==='json'){const data=JSON.parse(new TextDecoder().decode(buffer));if(!['sheet','document'].includes(data.kind)||!data.snapshot)throw Error('Invalid native snapshot');return await open(data.kind,randomId(),data.snapshot);}
  if(!confirm('Import as a LIMITED editable copy; original untouched. XLSX values/formulas only (formatting, merges, charts, metadata lost). DOCX semantic paragraphs/headings/tables only (page layout, styles, comments, tracked changes not preserved). Unsupported content may be rejected. Continue?'))return;
  const {decodeOffice}=await import('./office-sync.js');
  if(!['xlsx','docx'].includes(ext))throw Error('Unsupported format');
  const importedKind=ext==='xlsx'?'sheet':'document', importedId=randomId();
  const decoded=await decodeOffice(buffer,importedKind);if(uploadGeneration!==officeGeneration)throw Error('Document changed during upload conversion; original retained');
  await open(importedKind,importedId,decoded);
  if(id!==importedId)throw Error('Upload was not opened; original file unchanged');
  let bytes='';for(const byte of new Uint8Array(buffer))bytes+=String.fromCharCode(byte);
  const importedGeneration=officeGeneration;
  const nativeHash=await snapshotHash(adapter.snapshot());
  if(id!==importedId||officeGeneration!==importedGeneration)throw Error('Document changed during upload; original retained');
  await api('sync',{action:'publish',document_id:importedId,extension:ext,base:null,bytes:btoa(bytes),native_hash:nativeHash});
 }catch(e){report(e.message)}finally{officeUploading=false;e.target.value=''}
};
// Silence finalizes files locally; no vendor recognition or partial-STT claims.
$('listen').onclick=async()=>{
 if(opening||!adapter||saveBlocked||officePaused)return;
 if(recordIdentity&&!recordIdentity.discard){if(!recordIdentity.acquiring)stopVoice();return;}
 const session={id,generation:controller.generation,discard:false,acquiring:true};recordIdentity=session;
 const valid=()=>recordIdentity===session&&!session.discard&&!opening&&!saveBlocked&&session.id===id&&session.generation===controller.generation;
 let stage='secure context';
 const voiceError=error=>{
  const name=error.name||'Error';
  const detail=stage==='microphone acquisition'&&name==='NotFoundError'?'No audio input device was found by this browser. Connect a microphone or select an available input in macOS Sound settings, then retry.':
   stage==='microphone acquisition'&&name==='NotAllowedError'?'Microphone access denied. Allow this site in Firefox/browser permissions and macOS Privacy & Security → Microphone, then retry.':
   stage==='microphone acquisition'&&name==='NotReadableError'?'Microphone could not be opened. Check the selected input and whether another app is using it.':
   stage==='recorder setup'&&name==='NotSupportedError'?'This browser could not start an audio recorder with a supported codec.':error.message;
  const message='Voice '+stage+' ('+name+'): '+detail;report(message);$('voice-status').textContent=message;
 };
 try{
  if(!isSecureContext||!navigator.mediaDevices)throw Error('Voice requires localhost or approved HTTPS');
  stage='microphone acquisition';
  session.media=await navigator.mediaDevices.getUserMedia({audio:true});
  if(!valid()){stopVoice(session);return;}
  stage='audio context initialization';session.context=new AudioContext();await session.context.resume();
  if(!valid()){stopVoice(session);return;}
  const source=session.context.createMediaStreamSource(session.media),analyser=session.context.createAnalyser();
  analyser.fftSize=2048;source.connect(analyser);const samples=new Float32Array(analyser.fftSize),gate=new PhraseGate();
  session.queue=new AudioQueue({onError:e=>{if(valid())report(e.message)}});
  function record(){
   if(!valid())return;
   const started=performance.now();gate.reset(started);
   let chunks=[],bytes=0,upload=false;
   stage='recorder setup';
   const current=new MediaRecorder(session.media);session.recorder=current;
   current.onerror=event=>{if(valid()){stopVoice(session);voiceError(event.error||Error('Audio recorder failed'));}};
   current.ondataavailable=e=>{
    bytes+=e.data.size;
    if(bytes>2*1024*1024){chunks=[];upload=false;if(current.state==='recording')current.stop();return;}
    if(e.data.size)chunks.push(e.data);
    if(performance.now()-started>=20000&&current.state==='recording'){upload=gate.started!==null;current.stop();}
   };
   current.onstop=()=>{
    if(!valid()){chunks=[];stopVoice(session);return;}
    // Suspended browser event loops cannot enforce a timer; never upload an overlong file.
    const blob=upload&&performance.now()-started<=20500?new Blob(chunks,{type:current.mimeType}):null;chunks=[];
    record();
    if(!blob?.size)return;
    const utterance=randomId();
    const accepted=session.queue.push(async signal=>{
     if(!valid())return;
     const form=new FormData();const extension=blob.type.includes('ogg')?'ogg':blob.type.includes('mp4')?'m4a':'webm';form.append('file',blob,'phrase.'+extension);
     const response=await fetch('/api/transcribe',{method:'POST',headers:{'X-Hermes-CSRF-Token':csrf},body:form,signal});
     const result=await response.json();if(!response.ok)throw Error(result.error||'Transcription failed');
     if(!valid()||signal.aborted)return;
     const text=result.text||result.transcript;if(!text)return;
     $('transcript').textContent='Final: '+text;
     // Recognition does not wait for full inference. Exact final Stop can cancel it.
     void controller.transcript(text,utterance,true);
     if(!valid())stopVoice(session);
    });
    if(!accepted)report('Voice transcription backlog full; phrase discarded. Please repeat after pending work completes.');
   };
   session.finish=send=>{upload=send;if(current.state==='recording')current.stop();};
   current.start(1000);
  }
  record();session.acquiring=false;
  session.timer=setInterval(()=>{
   if(!valid()){stopVoice(session);return;}
   analyser.getFloatTimeDomainData(samples);
   const rms=Math.sqrt(samples.reduce((sum,v)=>sum+v*v,0)/samples.length),now=performance.now();
   $('listen').textContent=rms>.018?'Listening — speech detected':'Listening — waiting for speech';
   const hadSpeech=gate.started!==null,final=gate.sample(rms,now);
   if(final||gate.rotate(now))session.finish(final||hadSpeech);
  },50);
  report('Microphone ON — silence finalizes phrases. Final Stop cancels after transcription; toolbar Pause cancels immediately.');
 }catch(e){const show=valid();stopVoice(session);if(show)voiceError(e)}
};
$('language').disabled=true;$('language').title='Language follows the existing configured STT service; no override supported';
// Office sync integration (independent of voice capture).
import {installAutoSync} from './auto-sync.js';
window.cowork.officeSync=installAutoSync({api,report,pause:pauseOffice,
 current:()=>adapter?({id,generation:officeGeneration,kind,snapshot:adapter.snapshot(),dirty:JSON.stringify(adapter.snapshot())!==saved,ready:!opening&&!saving&&!saveBlocked&&!officeUploading}):null,
 reload:async (snapshot,session,hash,offer_id)=>{
  const active=id,activeAdapter=adapter,activeKind=kind,generation=officeGeneration;
  const check=()=>{if(active!==id||adapter!==activeAdapter||generation!==officeGeneration||session.id!==active||session.generation!==generation||session.isCurrent?.()===false)throw Error('Office import generation changed');ensureLease(true);};
  check();stopVoice();controller.stop();$('editor').inert=true;
  opening=true;$('listen').disabled=true;let candidate;
  try{
   await save(true);check();if(saveBlocked)throw Error('Cannot preserve local native recovery snapshot');
   const host=document.createElement('div');host.style.cssText='width:100%;height:100%';
   if(activeKind==='sheet'){const {SheetAdapter}=await import('./sheet.js');check();candidate=new SheetAdapter(host,snapshot);}
   else candidate=new DocumentAdapter(host,snapshot);
   const normalized=candidate.snapshot(),json=JSON.stringify(normalized);
   const native_hash=await snapshotHash(normalized);check();
   const receipt={hash,native_hash,offer_id};let result;
   const latest=await api('document?id='+encodeURIComponent(active));check();revision=latest.document?.revision||0;
   try{result=await api('document',{document_id:active,kind:activeKind,revision,snapshot:normalized,office_import:receipt});}
   catch(error){
    // A dropped save response is ambiguous, not permission to repeat replacement.
    const loaded=await api('document?id='+encodeURIComponent(active));check();
    if(JSON.stringify(loaded.document?.office_import)!==JSON.stringify(receipt)||JSON.stringify(loaded.document?.snapshot)!==json)throw error;
    result=loaded;
   }
   check();
   for(const name of ['apply','undo','redo']){const native=candidate[name].bind(candidate);candidate[name]=(...args)=>{ensureLease();return native(...args)};}
   const old=adapter;adapter=candidate;candidate=undefined;$('editor').replaceChildren(host);old.destroy();
   revision=result.document.revision;saved=json;controller.open(active,adapter);
   report('External Office version imported — native Undo reset once; acknowledgment reconciles separately.');
   return {native_hash};
  }finally{candidate?.destroy();if(active===id&&generation===officeGeneration){opening=false;pauseOffice(officePaused);}}
 }
});
setInterval(save,1500);
setInterval(async()=>{if(!adapter||opening||saveBlocked)return;const active=id,claimStart=performance.now();try{await api('claim',{document_id:id});if(active===id)leaseUntil=claimStart+25000;}catch(error){if(active===id){pauseOffice(true);report(error.message+' — connection paused; draft retained.');}}},5000);
window.addEventListener('offline',()=>{pauseOffice(true);window.cowork.officeSync.disconnect();});
window.addEventListener('online',()=>window.cowork.officeSync.tick());
for(const type of ['beforeinput','keydown','pointerdown'])$('editor').addEventListener(type,event=>{try{if(opening)throw Error('Opening document');ensureLease();}catch(error){event.preventDefault();event.stopImmediatePropagation();report(error.message)}},true);
window.addEventListener('beforeunload',e=>{controller.stop();stopVoice();if(adapter&&JSON.stringify(adapter.snapshot())!==saved){e.preventDefault();e.returnValue='';}});
await open('document',new URLSearchParams(location.search).get('id'));
