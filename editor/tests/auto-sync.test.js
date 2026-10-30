import test from 'node:test';
import assert from 'node:assert/strict';
import {installAutoSync} from '../src/auto-sync.js';
function harness(){
 let c={id:'doc',generation:1,kind:'document',ready:true,snapshot:{type:'doc'},dirty:false},paused=true,mode='paused',reloads=0,drop=true;
 const calls=[]; const elements=[];
 const h=installAutoSync({current:()=>c,pause:v=>paused=v,report(){},waitMs:0,
  createElement:()=>{const e={remove(){}};elements.push(e);return e},mount(){},timer:()=>1,clearTimer(){},
  decode:async()=>({type:'doc',content:[]}),encode:async()=>new Uint8Array([1]),
  reload:async()=>{reloads++;return {native_hash:'normalized'}},
  api:async(_,b)=>{calls.push(b);if(b.action==='owner-status')return {state:mode,ownership:mode==='synced'?'webui':'external'};
   if(b.action==='resume')return {state:'external',hash:'external',offer_id:'offer',bytes:'AQ=='};
   if(b.action==='accept'){mode='synced';if(drop){drop=false;throw Error('dropped')}return {state:'synced',hash:'external'}};
   return {state:'preserved'};}});
 return {h,calls,elements,get paused(){return paused},get reloads(){return reloads},set(v){c=v}};
}
test('reconnect automatically reloads before enabling writers; dropped acknowledgment never reloads twice',async()=>{
 const x=harness();await x.h.tick();assert.equal(x.reloads,1);assert.equal(x.paused,true);
 await x.h.tick();assert.equal(x.reloads,1);assert.equal(x.paused,false);x.h.destroy();
});
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
for(const disconnected of [false,true])for(const boundary of ['decode','reload','accept'])test('current automatic sync '+(disconnected?'disconnect':'switch')+' during '+boundary+' quarantines late completion',async()=>{
 const gate=deferred(),entered=deferred(),calls=[],pauses=[];let c={id:'old',generation:1,kind:'document',ready:true,snapshot:{type:'doc'},dirty:false};
 const sync=installAutoSync({current:()=>c,pause:v=>pauses.push(v),report(){},waitMs:0,createElement:()=>({remove(){}}),mount(){},timer:()=>1,clearTimer(){},
  decode:async()=>{if(boundary==='decode'){entered.resolve();await gate.promise;}return {type:'doc'};},
  reload:async()=>{calls.push('reload');if(boundary==='reload'){entered.resolve();await gate.promise;}return {native_hash:'normalized'};},
  api:async(_,b)=>{calls.push(b.action);if(b.action==='owner-status')return {state:'paused',ownership:'external'};
   if(b.action==='resume')return {state:'external',hash:'external',offer_id:'offer',bytes:'AQ=='};
   if(b.action==='accept'){if(boundary==='accept'){entered.resolve();await gate.promise;}return {state:'synced'};}return {state:'preserved'};}});
 const tick=sync.tick();await entered.promise;if(disconnected)sync.disconnect();else c={...c,id:'new',generation:2};gate.resolve();await tick;
 assert.equal(pauses.includes(false),false);
 if(boundary==='decode')assert.equal(calls.includes('reload'),false);
 if(boundary!=='accept')assert.equal(calls.includes('accept'),false);
 sync.destroy();
});
