import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';
import {randomId,snapshotHash} from '../src/browser-capabilities.js';
import {PhraseGate,AudioQueue} from '../src/voice.js';

async function boot(){
 const elements=new Map(),locks=new Set(),pending=[],streams=[],instances=[];
 const element=()=>({style:{},textContent:'',value:'',disabled:false,children:[],classList:{contains:()=>false,toggle:()=>false},addEventListener(){},replaceChildren(...children){this.children=children},append(...children){this.children.push(...children)}});
 const document={getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},createElement:element,documentElement:element(),addEventListener(){}};
 class Adapter{constructor(el,snapshot){this.el=el;instances.push(this);if(snapshot?.fail)throw Error('Invalid snapshot');this.data=snapshot||{};}snapshot(){if(this.data?.failSnapshot)throw Error('Snapshot failed');return this.data}destroy(){this.destroyed=true}apply(){}undo(){}redo(){}}
 class Controller{generation=0;stop(){this.generation++}open(id,a){this.id=id;this.adapter=a}submit(){}transcript(){}}
 class Recorder{state='inactive';constructor(stream){this.stream=stream;if(context.failRecorder)throw Error('Recorder failed')}start(){if(context.failStart)throw Error('Start failed');this.state='recording'}stop(){this.state='inactive';this.onstop?.()}}
 const context={randomId,snapshotHash,PhraseGate,AudioQueue,AbortController,AbortSignal,AudioContext:class{resume(){return Promise.resolve()}close(){}createMediaStreamSource(){return {connect(){}}}createAnalyser(){return {fftSize:2048,getFloatTimeDomainData(){}}}},installOfficeSync:()=>({}),document,Controller,DocumentAdapter:Adapter,MediaRecorder:Recorder,window:{addEventListener(){}},navigator:{locks:{request:async(name,options,callback)=>{if(locks.has(name))return callback(null);locks.add(name);try{await callback({})}finally{locks.delete(name)}}},mediaDevices:{getUserMedia(){return new Promise(resolve=>pending.push(resolve))}}},crypto:{randomUUID:()=>String(Math.random())},performance:{now:()=>0},sessionStorage:{getItem:()=>null,setItem(){}},localStorage:{setItem(){}},history:{replaceState(){}},location:{search:'?id=first'},URLSearchParams,isSecureContext:true,clearInterval(){},setInterval(){},setTimeout,Blob,FormData,console,fetch:async(path,opts)=>({ok:true,text:async()=>'',json:async()=>path.includes('document?id=')?{profile:'default',document:context.loaded}:{document:{revision:1}}})};
 context.installAutoSync=({pause})=>{context.resume=()=>pause(false);return {disconnect(){}}};
 const source=(await fs.readFile(new URL('../src/main.js',import.meta.url),'utf8')).replace(/^import .*;\n/gm,'');
 vm.createContext(context);await vm.runInContext('(async()=>{'+source+'})()',context);
 context.resume();
 return {context,elements,locks,pending,instances,click:id=>elements.get(id).onclick(),resolve(){const track={stopped:false,stop(){this.stopped=true}},stream={getTracks:()=>[track]};streams.push(stream);pending.shift()(stream);return track}};
}
test('pending microphone acquisition is serialized and pause cleans its stream',async()=>{
 const h=await boot(),first=h.click('listen'),second=h.click('listen');assert.equal(h.pending.length,1);h.click('pause');const track=h.resolve();await Promise.all([first,second]);assert.equal(track.stopped,true);
});
test('failed replacement preserves editor, history and ownership',async()=>{
 const h=await boot(),old=h.context.window.cowork.adapter;h.context.loaded={kind:'document',snapshot:{fail:true}};h.elements.get('identity').value='bad';await h.click('reopen');assert.equal(old.destroyed,undefined);assert.equal(h.context.window.cowork.adapter,old);assert.equal(h.context.window.cowork.id,'first');assert.equal(h.locks.size,1);assert.match([...h.locks][0],/first$/);
});
for(const action of ['stop','new-doc','close','supersede'])test(`pending microphone cleanup on ${action}`,async()=>{
 const h=await boot(),pending=h.click('listen');
 if(action==='close')h.context.window.cowork.pauseVoice();
 else if(action==='supersede')h.context.window.cowork.controller.stop();
 else await h.click(action);
 const track=h.resolve();await pending;assert.equal(track.stopped,true);
});
for(const failure of ['failRecorder','failStart'])test(`microphone cleanup after ${failure}`,async()=>{
 const h=await boot();h.context[failure]=true;const pending=h.click('listen'),track=h.resolve();await pending;assert.equal(track.stopped,true);
});
test('failed candidate initialization disposes candidate and releases only new lock',async()=>{
 const h=await boot(),old=h.context.window.cowork.adapter;h.context.loaded={kind:'document',snapshot:{failSnapshot:true}};h.elements.get('identity').value='bad';await h.click('reopen');assert.equal(h.instances.at(-1).destroyed,true);assert.equal(h.context.window.cowork.adapter,old);assert.equal(old.destroyed,undefined);assert.equal(h.locks.size,1);
});
test('same-ID reopen reuses own editor and lock',async()=>{
 const h=await boot(),old=h.context.window.cowork.adapter;await h.click('reopen');assert.match(h.elements.get('status').textContent,/Ready/);assert.equal(h.context.window.cowork.adapter,old);assert.equal(h.locks.size,1);
});
