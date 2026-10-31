import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Controller} from '../src/controller.js';
const tick=()=>new Promise(r=>setTimeout(r,0));
test('answer retries original head identity with bound context before B exactly once',async()=>{
 const calls=[],applied=[];const c=new Controller(async b=>{calls.push(b);return {document_id:b.document_id,utterance_id:b.utterance_id,...(calls.length===1?{clarification:'Which text?'}:{operations:[{type:'document.append',text:'resolved'}]})}},()=>{});
 c.open('d',{context:()=>({kind:'document'}),apply:()=>applied.push(c.active.id)});
 const a=c.submit('A','a'),b=c.submit('B','b');await a;
 const reply=c.answer('a','hello');c.answer('a','duplicate');await reply;await b;await tick();
 assert.deepEqual(calls.map(b=>b.utterance_id),['a','a','b']);assert.deepEqual(applied,['a','b']);assert.match(calls[1].text,/Which text/);assert.match(calls[1].text,/hello/);
});
test('bounded composed replies fit the existing 20000 character endpoint',async()=>{
 const calls=[];const c=new Controller(async b=>{calls.push(b);return {document_id:'d',utterance_id:'a',clarification:'?'.repeat(2000)}},()=>{});c.open('d',{context:()=>({})});await c.submit('original','a');
 for(let i=0;i<10;i++)await c.answer('a','a'.repeat(2000));
 assert.ok(calls.every(b=>b.text.length<=20000));assert.ok(c.items[0].turns.length<=3);
});
for(const action of ['stop','switch','disconnect'])test('inflight answered command cannot apply late after '+action,async()=>{
 let finish,calls=0;const applied=[];const c=new Controller(b=>{calls++;return calls===1?Promise.resolve({...b,clarification:'Which?'}):new Promise(resolve=>finish=()=>resolve({...b,operations:[{type:'undo'}]}));},()=>{});c.open('d',{context:()=>({}),apply:()=>applied.push('applied')});const a=c.submit('A','a'),b=c.submit('B','b');await a;const answer=c.answer('a','hello');if(action==='switch')c.open('e',{});else c.stop();finish();await answer;await b;await tick();assert.deepEqual(applied,[]);assert.equal(calls,2);
});
for(const action of ['stop','switch','disconnect'])test('stale answer rejected after '+action,async()=>{
 let calls=0;const c=new Controller(async b=>{calls++;return {...b,clarification:'Which?'}},()=>{});c.open('d',{context:()=>({})});await c.submit('A','a');if(action==='switch')c.open('e',{});else c.stop();assert.equal(c.answer('a','stale'),undefined);assert.equal(calls,1);
});
test('answer error keeps draft and FIFO blocked until explicit successful reply',async()=>{
 let calls=0;const applied=[];const c=new Controller(async b=>{calls++;if(calls===2)throw Error('temporary failure');return {...b,...(calls===1?{clarification:'Which?'}:{operations:[{type:'undo'}]})}},()=>{});c.open('d',{context:()=>({}),apply:()=>applied.push(c.active.id)});const a=c.submit('A','a'),b=c.submit('B','b');await a;await c.answer('a','hello');assert.equal(c.items[0].reply,'hello');assert.equal(c.items[1].status,'Paused');assert.equal(c.paused,true);assert.equal(c.items[0].status,'Clarification');await c.answer('a','hello');await b;assert.deepEqual(applied,['a','b']);
});
