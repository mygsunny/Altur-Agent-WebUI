import {test} from 'node:test';
import assert from 'node:assert/strict';

test('controller cancels stop and document switch; final transcripts deduplicated', async()=>{
 const {Controller}=await import('../src/controller.js');
 let resolve, calls=0, applied=[];
 const c=new Controller(()=>{calls++;return new Promise(r=>resolve=r)},()=>{});
 c.open('a',{context:()=>({}),apply:o=>applied.push(o)});
 c.transcript('partial','u',false); assert.equal(calls,0);
 const p=c.transcript('set value','u',true); await Promise.resolve();
 assert.equal(calls,1); c.stop(); resolve({document_id:'a',utterance_id:'u',operations:[{type:'undo'}]}); await p;
 assert.equal(applied.length,0);
 await c.transcript('duplicate','u',true); assert.equal(calls,1);
 const q=c.submit('replace','v'); c.open('b',{context:()=>({}),apply:o=>applied.push(o)});
 resolve({document_id:'a',utterance_id:'v',operations:[{type:'undo'}]}); await q;
 assert.equal(applied.length,0);
});

test('manual editing during inference stays live and targeted latest application wins', async()=>{
 const {Controller}=await import('../src/controller.js');
 let resolve; const cells={A1:'old',B1:'unrelated'};
 const c=new Controller(()=>new Promise(r=>resolve=r),()=>{});
 c.open('a',{context:()=>({...cells}),apply:o=>{cells[o.range]=o.values[0][0]}});
 const p=c.submit('change A1','u'); cells.A1='human'; cells.B1='human other';
 resolve({document_id:'a',utterance_id:'u',operations:[{type:'sheet.set',range:'A1',values:[['AI']]}]}); await p;
 assert.deepEqual(cells,{A1:'AI',B1:'human other'});
});

test('foreign response and ambiguous intent never mutate', async()=>{
 const {Controller}=await import('../src/controller.js'); let applied=0;
 const c=new Controller(async()=>({document_id:'wrong',utterance_id:'u',operations:[{type:'undo'}]}),()=>{});
 c.open('a',{context:()=>({}),apply:()=>applied++}); await c.submit('undo','u'); assert.equal(applied,0);
});
