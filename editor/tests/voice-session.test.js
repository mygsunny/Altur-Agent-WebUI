import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {PhraseGate,AudioQueue} from '../src/voice.js';
import {Controller} from '../src/controller.js';
import {execFileSync} from 'node:child_process';
const source=process.env.COWORK_VOICE_BASELINE?execFileSync('git',['show',process.env.COWORK_VOICE_BASELINE+':editor/src/main.js'],{encoding:'utf8'}):fs.readFileSync(new URL('../src/main.js',import.meta.url),'utf8');
function harness(){
 const elements=new Map();const $=id=>{if(!elements.has(id))elements.set(id,{textContent:''});return elements.get(id)};
 let pending=[];const tracks=[];const contexts=[];
 const context=vm.createContext({$,PhraseGate,AudioQueue,AbortController,Blob,FormData,crypto,performance,clearInterval,setInterval:()=>1,isSecureContext:true,report:()=>{},navigator:{mediaDevices:{getUserMedia:()=>new Promise((resolve,reject)=>pending.push({resolve,reject}))}},AudioContext:class{constructor(){contexts.push(this)}resume(){return Promise.resolve()}close(){this.closed=true}createMediaStreamSource(){return {connect(){}}}createAnalyser(){return {fftSize:2048,getFloatTimeDomainData(){}}}},MediaRecorder:class{constructor(){this.state='inactive'}start(){this.state='recording'}stop(){this.state='inactive';this.onstop?.()}},fetch:()=>{throw Error('unexpected request')}});
 vm.runInContext("let id='old',opening=false,adapter={},saveBlocked=false,officePaused=false; const controller={generation:0,stop(){this.generation++}};let recorder,media,recordIdentity,acquiring=false,voiceContext,voiceTimer,voiceAbort,voiceQueue=Promise.resolve();",context);
 const stop=source.slice(source.indexOf('function stopVoice('),source.indexOf('async function save('));
 const listen=source.slice(source.indexOf("$('listen').onclick=async()=>"),source.indexOf("$('language').disabled"));
 vm.runInContext(stop+listen,context);
 return {$,context,pending,tracks,contexts,run:s=>vm.runInContext(s,context),resolve(n){const track={stopped:false,stop(){this.stopped=true}};tracks[n]=track;pending[n].resolve({getTracks:()=>[track]})}};
}
for(const switchDoc of [false,true])test(`stale acquisition cannot clean newer session after ${switchDoc?'switch':'pause'}`,async()=>{
 const h=harness(),old=h.$('listen').onclick();h.run('stopVoice();'+(switchDoc?"id='new';":''));
 const fresh=h.$('listen').onclick();assert.equal(h.pending.length,2);h.resolve(1);await fresh;h.resolve(0);await old;
 assert.equal(h.tracks[0].stopped,true);assert.equal(h.tracks[1].stopped,false);assert.equal(h.contexts[0].closed,undefined);
});
for(const switchDoc of [false,true])test(`late failed permission cannot clean newer session after ${switchDoc?'switch':'pause'}`,async()=>{
 const h=harness(),old=h.$('listen').onclick();h.run('stopVoice();'+(switchDoc?"id='new';":''));
 const fresh=h.$('listen').onclick();h.resolve(1);await fresh;h.pending[0].reject(Error('Permission denied'));await old;
 assert.equal(h.tracks[1].stopped,false);assert.equal(h.contexts[0].closed,undefined);assert.match(h.$('listen').textContent||'Enable voice',/Enable|Listening/);
});
for(const success of [false,true])test(`Listen rejected during delayed ${success?'successful':'failed'} open`,async()=>{
 const h=harness();h.run('opening=true');const blocked=h.$('listen').onclick();assert.equal(h.pending.length,0);await blocked;
 h.run("opening=false;"+(success?"id='new';":''));const enabled=h.$('listen').onclick();h.resolve(0);await enabled;assert.equal(h.tracks[0].stopped,false);
});
test('source capture discards long idle segments and uploads bounded subsequent phrase',async()=>{
 const h=harness(),uploads=[];Object.assign(h.context,{clock:0,level:0,uploads,csrf:'',setInterval:fn=>{h.context.tick=fn;return 1},performance:{now:()=>h.context.clock}});
 h.run(`AudioContext.prototype.createAnalyser=function(){return {fftSize:2048,getFloatTimeDomainData(samples){samples.fill(level)}}};
 MediaRecorder.prototype.start=function(){this.state='recording';this.started=clock};
 MediaRecorder.prototype.stop=function(){this.state='inactive';this.ondataavailable({data:new Blob([String(clock-this.started)])});this.onstop()};
 fetch=async (url,opts)=>{uploads.push(Number(await opts.body.get('file').text()));return {ok:true,json:async()=>({text:''})}};`);
 const enabled=h.$('listen').onclick();h.resolve(0);await enabled;
 for(let now=0;now<125000;now+=50){h.context.clock=now;h.context.level=now>=120000&&now<120500?.1:0;h.context.tick();await new Promise(r=>setImmediate(r));}
 assert.equal(uploads.length,1);assert.ok(uploads[0]<=20000);h.run('stopVoice()');
});
for(const switchDoc of [false,true])test(`old inference completion cannot stop re-enabled microphone after ${switchDoc?'switch':'pause'}`,async()=>{
 const h=harness();Object.assign(h.context,{clock:0,level:.1,csrf:'',setInterval:fn=>{h.context.tick=fn;return 1},performance:{now:()=>h.context.clock}});
 h.run(`AudioContext.prototype.createAnalyser=function(){return {fftSize:2048,getFloatTimeDomainData(samples){samples.fill(level)}}};
 MediaRecorder.prototype.stop=function(){this.state='inactive';this.ondataavailable({data:new Blob(['audio'])});this.onstop()};
 controller.transcript=()=>new Promise(r=>globalThis.finishIntent=r);
 fetch=async()=>({ok:true,json:async()=>({text:'append a paragraph'})});`);
 const enabled=h.$('listen').onclick();h.resolve(0);await enabled;
 for(const [clock,level] of [[0,.1],[300,.1],[1200,0]]){Object.assign(h.context,{clock,level});h.context.tick();await new Promise(r=>setImmediate(r));}
 assert.equal(h.run('typeof finishIntent'),'function');h.run('stopVoice();'+(switchDoc?"id='new';":''));
 const fresh=h.$('listen').onclick();h.resolve(1);await fresh;h.run('finishIntent()');await new Promise(r=>setImmediate(r));
 assert.equal(h.tracks[1].stopped,false);assert.equal(h.contexts[1].closed,undefined);h.run('stopVoice()');
});
test('session resource cleanup is idempotent across Stop and delayed recorder stop event',async()=>{
 const h=harness();h.run('AudioContext.prototype.close=function(){this.closeCalls=(this.closeCalls||0)+1;if(this.closeCalls>1)throw Error("double close")}');
 const enabled=h.$('listen').onclick();h.resolve(0);await enabled;h.run('stopVoice()');assert.equal(h.contexts[0].closeCalls,1);
});
test('recorder data events rotate idle even if analyser timer is delayed',async()=>{
 const h=harness();Object.assign(h.context,{clock:0,performance:{now:()=>h.context.clock}});
 const enabled=h.$('listen').onclick();h.resolve(0);await enabled;
 const old=h.run('recordIdentity.recorder');h.context.clock=60000;old.ondataavailable({data:new Blob(['idle'])});
 assert.notEqual(h.run('recordIdentity.recorder'),old);h.run('stopVoice()');
});
test('capture recognizes final Stop while previous full inference is still pending',async()=>{
 const h=harness();let inferenceSignal,recognitions=0;
 const real=new Controller((body,signal)=>{inferenceSignal=signal;return new Promise(()=>{})},()=>{});real.open('old',{context:()=>({}),apply(){assert.fail('no late edit')}});
 Object.assign(h.context,{real,clock:0,level:.1,csrf:'',setInterval:fn=>{h.context.tick=fn;return 1},performance:{now:()=>h.context.clock},fetch:async()=>({ok:true,json:async()=>({text:++recognitions===1?'append content':'Stop'})})});
 h.run(`controller.transcript=real.transcript.bind(real);AudioContext.prototype.createAnalyser=function(){return {fftSize:2048,getFloatTimeDomainData(samples){samples.fill(level)}}};MediaRecorder.prototype.stop=function(){this.state='inactive';this.ondataavailable({data:new Blob(['audio'])});this.onstop()};`);
 const enabled=h.$('listen').onclick();h.resolve(0);await enabled;
 for(const [clock,level] of [[0,.1],[300,.1],[1200,0],[1500,.1],[1800,.1],[2700,0]]){Object.assign(h.context,{clock,level});h.context.tick();await new Promise(r=>setImmediate(r));}
 const aborted=inferenceSignal?.aborted;real.stop();h.run('stopVoice()');assert.equal(recognitions,2);assert.equal(aborted,true);
});
test('opening beginning during AudioContext resume invalidates setup',async()=>{
 const h=harness();h.run('AudioContext.prototype.resume=function(){return new Promise(r=>globalThis.resume=r)}');
 const enabled=h.$('listen').onclick();h.resolve(0);await new Promise(r=>setImmediate(r));h.run('opening=true;resume()');await enabled;assert.equal(h.tracks[0].stopped,true);
});
