// Local energy detection only; the configured server returns final, not partial, text.
export class PhraseGate {
 constructor(){this.reset();}
 reset(now=0){this.started=null;this.last=null;this.segmentStart=now;}
 rotate(now){return now-this.segmentStart>=20000;}
 sample(level,now){
  if(level>.018){if(this.started===null)this.started=now;this.last=now;}
  if(this.started!==null&&((now-this.last>=800&&this.last-this.started>=180)||now-this.started>=20000)){this.reset(this.segmentStart);return true;}
  if(this.started!==null&&now-this.last>=800)this.reset(this.segmentStart);
  return false;
 }
}

// Bounded retained jobs; deadline covers the entire request including body parsing.
export class AudioQueue {
 constructor({limit=3,timeout=30000,onError=()=>{}}={}){this.limit=limit;this.timeout=timeout;this.onError=onError;this.size=0;this.tail=Promise.resolve();this.abort=new AbortController();}
 close(){this.abort.abort();}
 push(run){
  if(this.size>=this.limit||this.abort.signal.aborted)return false;
  this.size++;
  const task=this.tail.then(async()=>{
   if(this.abort.signal.aborted)return;
   const abort=new AbortController();let timer;
   const cancel=()=>abort.abort();this.abort.signal.addEventListener('abort',cancel,{once:true});
   try{await Promise.race([run(abort.signal),new Promise((_,reject)=>{
    abort.signal.addEventListener('abort',()=>reject(Error('Voice request canceled or timed out')),{once:true});
    timer=setTimeout(()=>abort.abort(),this.timeout);
   })]);}catch(e){if(!this.abort.signal.aborted)this.onError(e);}finally{clearTimeout(timer);this.abort.signal.removeEventListener('abort',cancel);}
  }).finally(()=>{this.size--;});
  this.tail=task;return task;
 }
}
