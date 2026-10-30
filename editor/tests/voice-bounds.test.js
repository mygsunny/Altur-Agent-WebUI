import test from 'node:test';
import assert from 'node:assert/strict';
import * as voice from '../src/voice.js';
const {PhraseGate,AudioQueue}=voice;
import {Controller} from '../src/controller.js';
test('idle rotates wallclock segments; subsequent phrase stays bounded',()=>{
 const gate=new PhraseGate();let start=0,uploaded=[];
 for(let now=0;now<125000;now+=50){const speech=now>=120000&&now<120500;const final=gate.sample(speech?.1:0,now);if(final||gate.rotate(now)){if(final)uploaded.push(now-start);start=now;gate.reset(now);}}
 assert.equal(uploaded.length,1);assert.ok(uploaded[0]<=20000);
});
test('audio backlog is capped and timed out STT releases capacity',async()=>{
 let calls=0;const q=new AudioQueue({limit:2,timeout:15});
 const a=q.push(()=>{calls++;return new Promise(()=>{})});const b=q.push(async()=>{calls++;});
 assert.equal(q.push(async()=>{calls++}),false);await Promise.all([a,b]);assert.equal(calls,2);assert.equal(q.size,0);
});
test('inference deadline releases ordered voice work and reports timeout',async()=>{
 let signal;const reports=[];const c=new Controller((body,s)=>{signal=s;return new Promise(()=>{})},text=>reports.push(text));c.inferenceTimeout=10;c.open('doc',{context:()=>({}),apply(){}});
 const pending=c.transcript('append content','slow',true);await new Promise(r=>setTimeout(r,35));
 const aborted=signal.aborted;c.stop();await pending;assert.equal(aborted,true);assert.ok(reports.some(x=>/timed out/.test(x)));
});
test('recognized Stop cancels earlier inference without waiting for it',async()=>{
 let signal;const c=new Controller((body,s)=>{signal=s;return new Promise(()=>{})},()=>{});c.open('doc',{context:()=>({}),apply:()=>assert.fail('stale apply')});
 c.transcript('append something','first',true);await new Promise(r=>setTimeout(r,0));c.transcript('Stop','second',true);assert.equal(signal.aborted,true);
});
