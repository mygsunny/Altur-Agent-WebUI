import test from 'node:test';
import assert from 'node:assert/strict';
import {Controller} from '../src/controller.js';
for(const text of ['请添加一段文字,测试成功。','Append a paragraph that says hello.'])test('instruction echo asks clarification: '+text,async()=>{
 let applied=0,status='';const c=new Controller(async()=>({document_id:'a',utterance_id:'u',operations:[{type:'document.append',text}]}),s=>status=s);
 c.open('a',{context:()=>({}),apply:()=>applied++});await c.submit(text,'u');assert.equal(applied,0);assert.match(status,/clarify/i);
});
