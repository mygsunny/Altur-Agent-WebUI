import {randomId} from './browser-capabilities.js';
// Unified typed/final-speech FIFO. Capture intent text and document identity at
// admission; capture live context only when that entry reaches the head.
export class Controller {
 constructor(infer,report,setBusy=()=>{},onQueue=()=>{}){Object.assign(this,{infer,report,setBusy,onQueue,generation:0,seen:new Set(),pending:new Set(),items:[],history:[],queue:[],paused:false,pauseReason:'',active:null,queueLimit:8});}
 notify(){const completed=this.items.filter(i=>['Applied','Canceled'].includes(i.status));this.history.push(...completed.map(({id,status})=>({id,status})));this.history=this.history.slice(-10);this.items=this.items.filter(i=>!completed.includes(i));this.onQueue(this.items.map(({text,id,document_id,status,error})=>({text,id,document_id,status,error})));this.setBusy(!!this.active);}
 open(id,adapter){this.stop();this.id=id;this.adapter=adapter;}
 stop(){this.generation++;for(const abort of this.pending)abort.abort();this.pending.clear();for(const item of this.items)if(['Waiting','Running','Paused'].includes(item.status)){item.status='Canceled';item.resolve?.();}this.queue=[];this.active=null;this.paused=false;this.pauseReason='';this.notify();this.report('Stopped active and queued commands. Completed edits remain; Undo reverses the latest edit.');}
 transcript(text,id,final){
  if(!final||this.seen.has(id))return;
  // Stop bypasses the inference FIFO; ordinary new speech never cancels work.
  if(/^(stop|停止|停下)[.!。！\s]*$/iu.test(text.trim())){this.seen.add(id);this.stop();return;}
  return this.submit(text,id,'voice');
 }
 submit(text,id=randomId(),source='typed'){
  if(this.seen.has(id)||typeof text!=='string'||!text.trim())return;
  if(this.paused){this.report('Command queue paused: '+this.pauseReason+'. Stop AI discards waiting commands; resolve this barrier before resubmitting.');return;}
  const duplicate=source==='typed'&&this.items.find(e=>e.source==='typed'&&e.document_id===this.id&&e.text===text&&['Waiting','Running'].includes(e.status));if(duplicate)return duplicate.done;
  if(this.queue.length+(this.active?1:0)>=this.queueLimit){this.report('Command queue full; this command was not accepted. Pause voice and wait for the queue to drain before resubmitting.');return;}
  const item={status:'Waiting'};Object.defineProperties(item,Object.fromEntries(Object.entries({text,id,document_id:this.id,adapter:this.adapter,generation:this.generation,source}).map(([k,value])=>[k,{value,enumerable:true}])));
  item.done=new Promise(resolve=>item.resolve=resolve);this.seen.add(id);this.items.push(item);this.queue.push(item);this.notify();void this.next();return item.done;
 }
 dismiss(id){this.items=this.items.filter(i=>i.id!==id||!['Failed','Clarification'].includes(i.status));this.notify();}
 retry(id){const item=this.items.find(i=>i.id===id&&i.status==='Failed');if(!item||this.paused||item.generation!==this.generation||item.adapter!==this.adapter)return;const done=this.submit(item.text,randomId(),item.source);if(done)this.dismiss(id);return done;}
 async next(){
  if(this.active||this.paused||!this.queue.length)return;
  const item=this.queue.shift();if(item.generation!==this.generation||item.adapter!==this.adapter){item.status='Canceled';item.resolve();this.notify();void this.next();return;}
  this.active=item;item.status='Running';const abort=new AbortController();this.pending.add(abort);this.notify();let timedOut=false;
  const current=()=>item.generation===this.generation&&item.adapter===this.adapter&&this.active===item;
  const pause=(status,message,reason='document ambiguity')=>{item.status=status;item.error=message;this.paused=true;this.pauseReason=reason;for(const waiting of this.queue)waiting.status='Paused';this.report(message+' Queue paused ('+reason+'); Stop AI discards waiting commands before resolving this barrier.');};
  const timer=setTimeout(()=>{timedOut=true;abort.abort();},this.inferenceTimeout??30000);
  this.report('Inferring intent… manual editing remains available.');
  try{
   const canceled=new Promise((_,reject)=>abort.signal.addEventListener('abort',()=>reject(Error('Intent canceled')),{once:true}));
   const result=await Promise.race([this.infer({text:item.text,document_id:item.document_id,utterance_id:item.id,context:item.adapter.context()},abort.signal),canceled]);
   if(!current()||abort.signal.aborted)return;
   if(result.document_id!==item.document_id||result.utterance_id!==item.id)throw Error('Intent identity mismatch; no edit applied');
   if(result.clarification){pause('Clarification',result.clarification);return;}
   if(!Array.isArray(result.operations)||result.operations.length!==1)throw Error('Expected one coherent operation; no edit applied');
   const operation=result.operations[0],normalize=value=>value.normalize('NFKC').replace(/[\s\p{P}]/gu,'').toLowerCase();
   if(typeof operation.text==='string'&&normalize(operation.text)===normalize(item.text)){pause('Clarification','Please clarify the exact content to insert (quote it separately from the editing instruction). 请明确要插入的正文。');return;}
   if(operation.type==='stop'){this.stop();return;}
   // No await between live adapter validation and native transaction commit.
   item.adapter.apply(operation);item.status='Applied';this.report('Applied. Human and AI share native Undo / Redo.');
  }catch(error){if(current()){if(error.barrier)pause('Failed',error.message,error.barrier);else if(!abort.signal.aborted||timedOut){item.status='Failed';item.error=timedOut?'Intent timed out; no edit applied. No automatic retry was sent.':error.message;this.report(item.error+' Remaining commands continue; retry only explicitly.');}}}
  finally{clearTimeout(timer);this.pending.delete(abort);item.resolve();if(this.active===item)this.active=null;this.notify();if(item.generation===this.generation)void this.next();}
 }
}
