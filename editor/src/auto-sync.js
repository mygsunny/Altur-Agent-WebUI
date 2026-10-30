import {decodeOffice,encodeOffice} from './office-sync.js';
const fingerprint=async snapshot=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(snapshot)))),b=>b.toString(16).padStart(2,'0')).join('');
const b64=bytes=>{let s='';for(const b of new Uint8Array(bytes))s+=String.fromCharCode(b);return btoa(s)};
// Heartbeat is browser presence, NOT remote Office/iCloud-upload completion.
export function installAutoSync({api,current,reload,pause,report,waitMs=5000,
 decode=decodeOffice,encode=encodeOffice,createElement=()=>document.createElement('button'),
 mount=e=>document.getElementById('save-status').after(e),timer=setInterval,clearTimer=clearInterval}){
 let session,busy=false,dead=false,pending,until=0,baseline,publishedHash,conflict=false,reconnecting=true,lastResponse=Date.now();
 const button=createElement();button.textContent='Use arriving Office version (draft preserved)';button.hidden=true;mount(button);
 const valid=s=>{const c=current();return !dead&&c&&s===session&&c.id===s.id&&c.generation===s.generation};
 const show=message=>report('Office: '+message);
 const freeze=()=>{pause(true);until=Date.now()+waitMs;reconnecting=true;if(session){const next={...session};next.isCurrent=()=>valid(next);session=next;}if(!pending?.committed){pending=undefined;button.hidden=true;}};
 async function preserve(s){const c=current();if(!valid(s))return;await api('sync',{action:'preserve-draft',document_id:s.id,kind:s.kind,snapshot:c.snapshot});}
 async function acknowledge(s,p){
  const r=await api('sync',{action:'accept',document_id:s.id,hash:p.hash,offer_id:p.offer_id,native_hash:p.native_hash});
  if(!valid(s)||pending!==p)return;
  if(r.state!=='synced'){pending=undefined;freeze();return;}
  baseline=publishedHash=p.native_hash;pending=undefined;conflict=false;reconnecting=false;lastResponse=Date.now();button.hidden=true;pause(false,p.offer_id);
  show('WebUI connected; automatic same-file save. Remote upload completion is not inferred.');
 }
 async function apply(s,p){
  if(!valid(s))return;
  if(!p.committed){await preserve(s);if(!valid(s))return;const r=await reload(p.snapshot,s,p.hash,p.offer_id);if(!valid(s))return;p.native_hash=r.native_hash;baseline=p.native_hash;p.committed=true;}
  await acknowledge(s,p);
 }
 button.onclick=async()=>{if(busy||!pending)return;const s=session,p=pending;busy=true;try{await apply(s,p)}catch(e){if(valid(s))show('reconciliation pending: '+e.message)}finally{busy=false}};
 async function tick(){
  if(busy||dead)return;const c=current();if(!c?.ready)return;
  if(!session||session.id!==c.id||session.generation!==c.generation){session={id:c.id,generation:c.generation,kind:c.kind};pending=undefined;baseline=publishedHash=undefined;conflict=false;button.hidden=true;freeze();}
  const s=session;busy=true;
  try{
   if(pending){if(pending.committed&&Date.now()>=until)await acknowledge(s,pending);return;}
   const r=await api('sync',{action:'owner-status',document_id:s.id});if(!valid(s))return;lastResponse=Date.now();
   if(r.state==='disabled'){pause(false);return;}
   const hash=await fingerprint(c.snapshot);if(!valid(s))return;
   if(r.state==='unbound'){
    await preserve(s);if(!valid(s))return;
    const bytes=await encode(c.snapshot,s.kind);if(!valid(s))return;
    await api('sync',{action:'publish',document_id:s.id,extension:s.kind==='sheet'?'xlsx':'docx',base:null,bytes:b64(bytes),native_hash:hash});
    return;
   }
   if(r.ownership==='webui'){
    if(reconnecting){await api('sync',{action:'yield',document_id:s.id});return;}
    pause(false,r.lease_id);
    if(r.native_hash&&hash!==r.native_hash){
     const bytes=await encode(c.snapshot,s.kind);if(!valid(s)||JSON.stringify(current().snapshot)!==JSON.stringify(c.snapshot))return;
     const result=await api('sync',{action:'owner-publish',document_id:s.id,connection_grant:r.lease_id,base:r.hash,bytes:b64(bytes),native_hash:hash});
     if(!valid(s))return;
     if(result.ownership!=='webui'){await preserve(s);freeze();conflict=true;show('external change; copies preserved; reconciling');}
     else publishedHash=hash;
    }
    return;
   }
   pause(true);
   if(Date.now()<until){show('waiting for stable arriving cloud file; connection is not upload completion');return;}
   await preserve(s);if(!valid(s))return;
   const offered=await api('sync',{action:'resume',document_id:s.id});if(!valid(s))return;
   if(offered.state!=='external'){show(offered.state+' — writes paused');return;}
   const snapshot=await decode(Uint8Array.from(atob(offered.bytes),x=>x.charCodeAt(0)),s.kind);if(!valid(s))return;
   pending={...offered,snapshot};
   // A changed draft after reconciliation is a conflict, not cloud arrival order.
   if(conflict||(baseline&&hash!==baseline)){button.hidden=false;show('draft and Office version preserved; choose arriving version or export draft');return;}
   await apply(s,pending);
  }catch(e){if(valid(s)){if(!reconnecting)baseline=publishedHash;freeze();show('paused/retry: '+e.message)}}finally{busy=false;}
 }
 const clock=timer(tick,2000);
 const watchdog=timer(()=>{if(Date.now()-lastResponse>8000&&!reconnecting){baseline=publishedHash;freeze();}},1000);
 return {tick,disconnect(){baseline=publishedHash;freeze();},destroy(){dead=true;clearTimer(clock);clearTimer(watchdog);button.remove();}};
}
