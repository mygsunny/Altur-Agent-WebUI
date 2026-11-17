import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {randomId,snapshotHash} from '../src/browser-capabilities.js';
const source=fs.readFileSync(new URL('../src/main.js',import.meta.url),'utf8');
function harness(){
 const calls=[],elements=new Map();let finishSave,finishCommit;
 const $=id=>{if(!elements.has(id))elements.set(id,{replaceChildren(){calls.push(['swap'])}});return elements.get(id)};
 const context=vm.createContext({randomId,snapshotHash,$,crypto,TextEncoder,Uint8Array,JSON,document:{createElement:()=>({style:{}})},window:{cowork:{}},installOfficeSync:config=>config,ensureLease(){},stopVoice(){},report(){},controller:{stop(){},open(){calls.push(['controller'])}},DocumentAdapter:class{snapshot(){return {type:'doc',content:[{type:'paragraph'}]}}destroy(){calls.push(['destroyCandidate'])}},save:()=>new Promise(r=>finishSave=r),api:async(path,body)=>{if(path.startsWith('document?id='))return {document:{revision:1}};calls.push([path,body]);if(path==='document')return new Promise(r=>finishCommit=r);throw Error('unexpected read')}});
 vm.runInContext("let id='old',kind='document',officeGeneration=1,adapter={destroy(){},snapshot(){return {type:'doc'}}},saved='',revision=1,opening=false,saving=false,saveBlocked=false,officeUploading=false;",context);
 context.installAutoSync=context.installOfficeSync;context.pauseOffice=()=>{};context.officePaused=true;
 vm.runInContext(source.slice(source.indexOf('window.cowork.officeSync=installAutoSync'),source.indexOf('setInterval(save')),context);
 return {context,calls,run:s=>vm.runInContext(s,context),reload:()=>context.window.cowork.officeSync.reload({type:'doc'},{id:'old',generation:1},'a'.repeat(64)),save(){finishSave()},commit(){finishCommit({document:{revision:2}})}};
}
test('switch during preserve save cannot replace another editor',async()=>{
 const h=harness(),result=h.reload();h.run("id='new';officeGeneration=2");h.save();await assert.rejects(result,/generation/);assert.equal(h.calls.length,0);
});
test('switch during native commit cannot swap another editor or acknowledge it',async()=>{
 const h=harness(),result=h.reload();h.save();await new Promise(r=>setTimeout(r,20));
 assert.equal(h.calls[0][1].document_id,'old');h.run("id='new';officeGeneration=2");h.commit();await assert.rejects(result,/generation/);
 assert.equal(h.calls.some(c=>c[0]==='swap'),false);
});
