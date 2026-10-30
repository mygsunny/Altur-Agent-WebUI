import {randomId} from './browser-capabilities.js';
// One synchronous adapter commit boundary, never an AI snapshot replacement.
export class Controller {
 constructor(infer, report) { this.infer=infer; this.report=report; this.generation=0; this.seen=new Set(); this.pending=new Set(); this.voiceTail=Promise.resolve(); this.voiceCount=0; }
 open(id, adapter) { this.stop(); this.id=id; this.adapter=adapter; }
 stop() { this.generation++; for(const abort of this.pending) abort.abort(); this.pending.clear(); this.voiceTail=Promise.resolve(); this.voiceCount=0; this.report('Stopped pending work. Completed edits remain; Undo reverses the latest edit.'); }
 transcript(text,id,final) { if(final&&this.seen.has(id))return;this.report(text); if(final) {
  if(/^(stop|停止|停下)[.!。！\s]*$/iu.test(text.trim())){this.seen.add(id);this.stop();return;}
  if(this.voiceCount>=3){this.report('Voice intent backlog full; phrase discarded. Please repeat after pending work completes.');return;}
  const generation=this.generation;this.voiceCount++;
  const task=this.voiceTail.then(()=>{if(generation===this.generation)return this.submit(text,id)}).finally(()=>{if(generation===this.generation)this.voiceCount--;});
  this.voiceTail=task;return task;
 } }
 async submit(text,id=randomId()) {
  if(this.seen.has(id)) return; this.seen.add(id);
  const generation=this.generation, document_id=this.id, adapter=this.adapter;
  const abort=new AbortController(); this.pending.add(abort);
  const timer=setTimeout(()=>{if(generation===this.generation)this.report('Intent timed out; no edit applied. Please repeat.');abort.abort();},this.inferenceTimeout??30000);
  this.report('Inferring intent… manual editing remains available.');
  try {
   const result=await Promise.race([this.infer({text,document_id,utterance_id:id,context:adapter.context()},abort.signal),new Promise((_,reject)=>abort.signal.addEventListener('abort',()=>reject(Error('Intent canceled or timed out')),{once:true}))]);
   if(generation!==this.generation || adapter!==this.adapter || abort.signal.aborted) return;
   if(result.document_id!==document_id || result.utterance_id!==id) throw Error('Intent identity mismatch; no edit applied');
   if(result.clarification) {this.report(result.clarification);return;}
   if(!Array.isArray(result.operations)||result.operations.length!==1) throw Error('Expected one coherent operation');
   const operation=result.operations[0];
   // A verbatim instruction/content echo is ambiguous, not permission to insert it.
   const normalize=value=>value.normalize('NFKC').replace(/[\s\p{P}]/gu,'').toLowerCase();
   if(typeof operation.text==='string'&&normalize(operation.text)===normalize(text)){
    this.report('Please clarify the exact content to insert (quote it separately from the editing instruction). 请明确要插入的正文。');return;
   }
   if(operation.type==='stop') {this.stop();return;}
   // No await between live target validation and native transaction commit.
   adapter.apply(operation);
   this.report('Applied. Human and AI share native Undo / Redo.');
  } catch(error) { if(!abort.signal.aborted && generation===this.generation) this.report(error.message); }
  finally {clearTimeout(timer);this.pending.delete(abort);}
 }
}
