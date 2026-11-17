import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../src/office-sync.js',import.meta.url),'utf8');
function harness(){
 const elements=[],calls=[];let c={id:'old',generation:1,ready:true,kind:'document',snapshot:{type:'doc'},dirty:false};let resolveDecode;
 const context=vm.createContext({crypto,TextEncoder,Uint8Array,btoa,atob,JSON,confirm:()=>true,setInterval:()=>1,clearInterval(){},document:{createElement(){const e={remove(){}};elements.push(e);return e},getElementById(){return {after(){}}}},decodeOffice:()=>new Promise(r=>resolveDecode=r),encodeOffice:async()=>new Uint8Array([1])});
 vm.runInContext(source.slice(source.indexOf('const b64=')).replace('export function','function')+';globalThis.install=installOfficeSync',context);
 let reloads=0,accepts=0,acceptHook,reloadHook;
 const sync=context.install({current:()=>c,report(){},reload:async()=>{reloads++;if(reloadHook)await reloadHook();return {native_hash:'normalized'}},api:async(_,body)=>{calls.push(body);if(body.action==='accept'){if(acceptHook)return acceptHook();if(++accepts===1)throw Error('dropped response');return {state:'synced'}};return {state:'external',bytes:'AQ==',hash:'external',native_hash:null}}});
 return {sync,elements,calls,onAccept(fn){acceptHook=fn},onReload(fn){reloadHook=fn},set(v){c=v},decode(v){resolveDecode(v)},get reloads(){return reloads}};
}
test('switch during decode cannot offer or import stale snapshot',async()=>{
 const h=harness(),tick=h.sync.tick();await new Promise(r=>setImmediate(r));h.set({id:'new',generation:2,ready:true,snapshot:{}});h.decode({type:'doc'});await tick;
 assert.equal(h.elements[1].hidden,true);assert.equal(h.reloads,0);
});
test('dropped accept response retries ack, never reloads twice',async()=>{
 const h=harness(),tick=h.sync.tick();await new Promise(r=>setImmediate(r));h.decode({type:'doc'});await tick;
 await h.elements[1].onclick();assert.equal(h.reloads,1);
 await h.sync.tick();assert.equal(h.reloads,1);assert.equal(h.calls.filter(c=>c.action==='accept').length,2);
});

test('switch during ack cannot clear new document state',async()=>{
 const h=harness(),tick=h.sync.tick();await new Promise(r=>setImmediate(r));h.decode({type:'doc'});await tick;
 let finish;h.onAccept(()=>new Promise(r=>finish=r));const importing=h.elements[1].onclick();await new Promise(r=>setImmediate(r));
 h.set({id:'new',generation:2,ready:true,snapshot:{}});finish({state:'synced'});await importing;
 const fresh=h.sync.tick();await new Promise(r=>setImmediate(r));h.decode({type:'doc'});await fresh;
 assert.equal(h.elements[1].hidden,false);assert.equal(h.calls.filter(c=>c.action==='accept').every(c=>c.document_id==='old'),true);
});
test('poll and repeated clicks cannot overlap a pending native save',async()=>{
 const h=harness(),tick=h.sync.tick();await new Promise(r=>setImmediate(r));h.decode({type:'doc'});await tick;
 let finish;h.onReload(()=>new Promise(r=>finish=r));const importing=h.elements[1].onclick();
 await h.elements[1].onclick();await h.sync.tick();assert.equal(h.reloads,1);assert.equal(h.calls.length,1);
 finish();await importing;
});
